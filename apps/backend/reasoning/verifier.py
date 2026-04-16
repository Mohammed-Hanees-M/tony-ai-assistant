import json
import re
from typing import Tuple
from apps.backend.schemas.reasoning import ReasoningTrace, VerificationReport
from apps.backend.llm.inference import run_llm_inference

VERIFIER_PROMPT = """
You are Tony's Internal Critic and Verification layer.
Analyze the provided user query, reasoning trace, and draft answer for:
1. Factual correctness
2. Logical consistency
3. Completeness
4. Contradictions or hallucinations
5. Missing edge cases

Output strictly as a JSON object adhering to this schema:
{
  "passed": true|false,
  "confidence_delta": 0.0 to -1.0 (or positive if extremely confident),
  "issues_found": ["issue 1", "issue 2"],
  "suggested_improvements": ["suggestion 1"],
  "revised_answer": "Complete rewritten answer fixing the issues (or mirror the draft if passed)",
  "verifier_notes": "Summary of your verification process"
}
Do NOT wrap your response in markdown blocks. Output pure JSON.
"""

# Deterministic Knowledge Layer for High-Trust Hotspots
FACTUAL_TRUTH_GUARD = {
    "cm of kerala": "Pinarayi Vijayan",
    "chief minister of kerala": "Pinarayi Vijayan",
    "pm of india": "Narendra Modi",
    "president of india": "Droupadi Murmu",
    "capital of kerala": "Thiruvananthapuram"
}

def extract_json(raw_text: str) -> str:
    try:
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_text, re.DOTALL)
        if match:
            return match.group(1)
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start != -1 and end != -1:
            return raw_text[start:end+1]
        return raw_text
    except:
        return raw_text

def parse_verifier_output(raw_output: str, original_draft: str) -> VerificationReport:
    try:
        json_str = extract_json(raw_output)
        data = json.loads(json_str)
        return VerificationReport(
            passed=bool(data.get("passed", False)),
            confidence_delta=float(data.get("confidence_delta", 0.0)),
            issues_found=data.get("issues_found", []),
            suggested_improvements=data.get("suggested_improvements", []),
            revised_answer=data.get("revised_answer", original_draft),
            verifier_notes=data.get("verifier_notes", "")
        )
    except Exception as e:
        print(f"[VERIFIER] Invalid output, falling back. Error: {e}")
        return VerificationReport(
            passed=False,
            confidence_delta=-0.5,
            issues_found=["Malformed verifier output"],
            suggested_improvements=[],
            revised_answer=original_draft,
            verifier_notes="System fallback due to parsing error."
        )

def verify_and_improve_answer(user_query: str, reasoning_trace: ReasoningTrace, draft_answer: str, max_iterations=2, model: str = "phi3") -> Tuple[str, VerificationReport]:
    current_draft = draft_answer
    report = None
    
    trace_dump = reasoning_trace.model_dump_json(indent=2)
    
    for i in range(max_iterations):
        print(f"\n[VERIFIER] Iteration {i+1} analyzing draft...")
        
        user_content = (
            f"User Query: {user_query}\n\n"
            f"Factual Truth Guard Reference: {json.dumps(FACTUAL_TRUTH_GUARD)}\n\n"
            f"Internal Reasoning Trace:\n{trace_dump}\n\n"
            f"Draft Answer: {current_draft}\n\n"
            "Evaluate this draft answer and provide your structured JSON report."
        )
        
        messages = [
            {"role": "system", "content": VERIFIER_PROMPT},
            {"role": "user", "content": user_content}
        ]
        
        raw_response = run_llm_inference(messages, model)
        report = parse_verifier_output(raw_response, current_draft)
        
        print(f"[VERIFIER] Passed: {report.passed} | Confidence Delta: {report.confidence_delta}")
        if report.issues_found:
            print(f"  - Issues found: {len(report.issues_found)}")
        
        if report.passed:
            print("[VERIFIER] Verification passed.")
            break
            
        print("[VERIFIER] Verification failed. Revising draft...")
        current_draft = report.revised_answer

    # Adjust confidence
    reasoning_trace.confidence = max(0.0, min(1.0, reasoning_trace.confidence + report.confidence_delta))
    print(f"[VERIFIER] Final confidence adjusted to: {reasoning_trace.confidence:.2f}")

    return current_draft, report
