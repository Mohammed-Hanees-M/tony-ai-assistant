from sqlalchemy.orm import Session

from apps.backend.llm.router import select_model
from apps.backend.llm.inference import run_llm_inference, is_error_response
from apps.backend.llm.prompt_manager import build_messages
from apps.backend.llm.context_builder import build_context
from apps.backend.llm.response_formatter import format_response

from apps.backend.core.config import CONTEXT_WINDOW_SIZE, PROMPT_TOKEN_BUDGET
from apps.backend.llm.token_budget import trim_messages_to_token_budget
from apps.backend.llm.memory_extractor import extract_long_term_memories
from apps.backend.llm.memory_retriever import retrieve_relevant_long_term_memories
from apps.backend.llm.memory_summarizer import summarize_conversation_chunk
from apps.backend.llm.episodic_extractor import extract_episodic_memories
from apps.backend.llm.episodic_retriever import retrieve_relevant_episodes
from apps.backend.llm.reflection_engine import extract_reflection, upsert_reflection
from apps.backend.llm.reflection_retriever import retrieve_relevant_reflections
from apps.backend.database.repositories.memory_repository import create_long_term_memory
from apps.backend.database.repositories.summary_repository import create_summary, get_all_summaries, get_latest_summary
from apps.backend.database.repositories.episode_repository import create_episodic_memory
from apps.backend.database.repositories.conversation_repository import (
    create_conversation,
    add_message,
    get_messages_after_id,
    get_conversation
)


def process_chat_message(
    db: Session,
    user_message: str,
    conversation_id: int | None = None
):
    if conversation_id is None:
        conversation = create_conversation(db)
        conversation_id = conversation.id
    else:
        conversation = get_conversation(db, conversation_id)
        if not conversation:
            raise ValueError("Conversation ID not found")
            
    # STEP 1: Summarization Retrieval
    # Fetch all previous summaries to set the starting point for active history
    summaries = get_all_summaries(db, conversation_id)
    latest_summary = get_latest_summary(db, conversation_id)
    last_summarized_id = latest_summary.covered_message_end_id if latest_summary else -1

    # STEP 2: Active History Retrieval
    # We only fetch messages that have NOT been summarized yet
    history = get_messages_after_id(db, conversation_id, last_summarized_id)

    # STEP 3: Semantic Retrieval of Long-Term Memories
    long_term_memories = retrieve_relevant_long_term_memories(db, user_message, limit=5)

    # STEP 4: Semantic Retrieval of Past Experiences (Episodes)
    episodes = retrieve_relevant_episodes(db, user_message, limit=3)

    # STEP 5: Semantic Retrieval of Learned Lessons (Reflections)
    reflections = retrieve_relevant_reflections(db, user_message, limit=3)

    # STEP 6: Build context using ALL preserved layers
    context = build_context(
        user_message=user_message, 
        history=history, 
        long_term_memories=long_term_memories,
        summaries=summaries,
        episodes=episodes,
        reflections=reflections
    )

    # Generate assistant response
    messages = build_messages(context)
    
    # Apply Token Budgeting
    messages = trim_messages_to_token_budget(messages, PROMPT_TOKEN_BUDGET)
    
    model = select_model(user_message, db=db)
    
    print(f"[DEBUG] Processing chat. Conversation: {conversation_id}. Summaries: {len(summaries)}. LTM: {len(long_term_memories)}. Episodes: {len(episodes)}. Reflections: {len(reflections)}")
    
    raw_response = run_llm_inference(messages, model)
    response = format_response(raw_response)

    # STEP 7: Conditional Persistence
    if is_error_response(response):
        print(f"[DEBUG] Inference failed. Skipping persistence for conversation {conversation_id}.")
    else:
        # Save user message to DB
        u_msg_obj = add_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=user_message
        )

        # Save assistant response to DB
        add_message(
            db=db,
            conversation_id=conversation_id,
            role="assistant",
            content=response
        )

        # STEP 8: Memory Summarization Trigger
        # If unsummarized history exceeds threshold, compress oldest chunk
        unsummarized = get_messages_after_id(db, conversation_id, last_summarized_id)
        SUMMARIZATION_THRESHOLD = 15
        SUMMARIZATION_CHUNK_SIZE = 10
        
        if len(unsummarized) >= SUMMARIZATION_THRESHOLD:
            chunk_to_summarize = unsummarized[:SUMMARIZATION_CHUNK_SIZE]
            summary_text = summarize_conversation_chunk([
                {"role": m.role, "content": m.content} for m in chunk_to_summarize
            ])
            
            if summary_text:
                create_summary(
                    db=db,
                    conversation_id=conversation_id,
                    text=summary_text,
                    start_id=chunk_to_summarize[0].id,
                    end_id=chunk_to_summarize[-1].id
                )
                print(f"[DEBUG] Summarization successful. Compressed messages {chunk_to_summarize[0].id}-{chunk_to_summarize[-1].id}.")

        # STEP 9: Long-Term Memory Extraction
        extracted_facts = extract_long_term_memories(user_message)
        if extracted_facts:
            print(f"[DEBUG] Extracted {len(extracted_facts)} long-term memories.")
            for e in extracted_facts:
                create_long_term_memory(
                    db=db,
                    key=e["key"],
                    value=e["value"],
                    category=e.get("category", "fact"),
                    importance=e["importance"],
                    source_message_id=u_msg_obj.id
                )

        # STEP 10: Episodic Memory Extraction
        # Capture current experience if significant
        new_episode = extract_episodic_memories(user_message, response)
        if new_episode:
            print(f"[DEBUG] Captured NEW episodic memory: {new_episode['summary']}")
            create_episodic_memory(
                db=db,
                conversation_id=conversation_id,
                event_type=new_episode["event_type"],
                summary=new_episode["summary"],
                outcome=new_episode["outcome"],
                importance=new_episode["importance"],
                tags=new_episode.get("tags", ""),
                embedding=new_episode.get("embedding")
            )
            
        # STEP 11: Reflective Memory (Learning) Stage
        # Identify if a meta-lesson was learned
        new_lesson = extract_reflection(user_message, response)
        if new_lesson:
            print(f"[DEBUG] Learned NEW reflection: {new_lesson['lesson']}")
            upsert_reflection(db, new_lesson)

    return response, conversation_id