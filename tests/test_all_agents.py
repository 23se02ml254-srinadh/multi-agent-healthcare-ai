import sys
import os
import time
import json

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)

from agents.coordinator import CoordinatorAgent
from agents.symptom_agent import SymptomAgent
from agents.disease_prediction_agent import DiseasePredictionAgent
from agents.medical_knowledge_agent import MedicalKnowledgeAgent
from agents.explainable_ai_agent import ExplainableAIAgent
from agents.recommendation_agent import RecommendationAgent
from agents.report_summary_agent import ReportSummaryAgent

def run_agent_tests():
    results = {}
    print("==================================================")
    print("       MULTI-AGENT SYSTEM UNIT TESTS")
    print("==================================================")

    # 1. SymptomAgent Test
    print("\n[TEST 1] SymptomAgent...")
    t0 = time.time()
    try:
        sa = SymptomAgent()
        s_res = sa.execute({'text': 'I have high fever, chills, cough, and severe headache for 3 days'})
        t1 = time.time()
        elapsed = t1 - t0
        passed = s_res.get('status') == 'success' and len(s_res.get('symptoms', [])) > 0
        results['SymptomAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'extracted_symptoms': s_res.get('symptoms', []),
            'response_snippet': s_res.get('response', '')[:100] + '...'
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
        print(f"  Extracted: {s_res.get('symptoms', [])}")
    except Exception as e:
        results['SymptomAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    # 2. DiseasePredictionAgent Test
    print("\n[TEST 2] DiseasePredictionAgent...")
    d_res = {}
    t0 = time.time()
    try:
        dpa = DiseasePredictionAgent()
        d_res = dpa.execute({'symptoms': ['fever', 'cough', 'headache', 'chills']})
        t1 = time.time()
        elapsed = t1 - t0
        passed = d_res.get('status') == 'success' and len(d_res.get('predictions', [])) > 0
        top_pred = d_res.get('predictions', [{}])[0] if d_res.get('predictions') else {}
        results['DiseasePredictionAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'top_prediction': top_pred.get('disease'),
            'confidence': top_pred.get('confidence'),
            'predictions_count': len(d_res.get('predictions', []))
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
        print(f"  Top Disease: {top_pred.get('disease')} (Confidence: {top_pred.get('confidence')})")
    except Exception as e:
        results['DiseasePredictionAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    # 3. MedicalKnowledgeAgent Test
    print("\n[TEST 3] MedicalKnowledgeAgent...")
    t0 = time.time()
    try:
        mka = MedicalKnowledgeAgent()
        k_res = mka.execute({'query': 'What is influenza and how to manage it?', 'symptoms': ['fever', 'cough']})
        t1 = time.time()
        elapsed = t1 - t0
        passed = k_res.get('status') == 'success' and len(k_res.get('response', '')) > 20
        results['MedicalKnowledgeAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'response_length': len(k_res.get('response', ''))
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
    except Exception as e:
        results['MedicalKnowledgeAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    # 4. ExplainableAIAgent Test
    print("\n[TEST 4] ExplainableAIAgent...")
    t0 = time.time()
    try:
        ea = ExplainableAIAgent()
        e_res = ea.execute({'symptoms': ['fever', 'cough'], 'prediction': d_res})
        t1 = time.time()
        elapsed = t1 - t0
        passed = e_res.get('status') == 'success' and len(e_res.get('response', '')) > 20
        results['ExplainableAIAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'response_length': len(e_res.get('response', ''))
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
    except Exception as e:
        results['ExplainableAIAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    # 5. RecommendationAgent Test
    print("\n[TEST 5] RecommendationAgent...")
    t0 = time.time()
    try:
        ra = RecommendationAgent()
        r_res = ra.execute({'symptoms': ['fever', 'cough'], 'disease': 'Common Cold'})
        t1 = time.time()
        elapsed = t1 - t0
        passed = r_res.get('status') == 'success' and len(r_res.get('recommendations', [])) > 0
        results['RecommendationAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'recommendations_count': len(r_res.get('recommendations', []))
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
        print(f"  Recommendations Count: {len(r_res.get('recommendations', []))}")
    except Exception as e:
        results['RecommendationAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    # 6. ReportSummaryAgent Test
    print("\n[TEST 6] ReportSummaryAgent...")
    t0 = time.time()
    try:
        rsa = ReportSummaryAgent()
        report_sample = (
            "PATIENT LAB REPORT\n"
            "Test Name: Complete Blood Count (CBC) and Lipid Profile\n"
            "Hemoglobin: 10.8 g/dL (Reference: 13.5 - 17.5 g/dL) - LOW\n"
            "White Blood Cell (WBC): 12,800 /mcL (Reference: 4,500 - 11,000 /mcL) - HIGH\n"
            "Total Cholesterol: 245 mg/dL (Reference: < 200 mg/dL) - HIGH\n"
            "Fasting Blood Glucose: 135 mg/dL (Reference: 70 - 99 mg/dL) - HIGH\n"
            "Platelets: 280,000 /mcL (Reference: 150,000 - 450,000 /mcL) - NORMAL\n"
            "Impression: Mild hypochromic anemia, elevated inflammatory markers, and hyperglycemia."
        )
        rpt_res = rsa.execute({'text': report_sample, 'file_name': 'cbc_test.txt', 'file_type': '.txt'})
        t1 = time.time()
        elapsed = t1 - t0
        passed = rpt_res.get('status') == 'success' and len(rpt_res.get('abnormal_values', [])) > 0
        results['ReportSummaryAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'findings_count': len(rpt_res.get('findings', [])),
            'abnormal_values_count': len(rpt_res.get('abnormal_values', [])),
            'abnormal_items': rpt_res.get('abnormal_values', [])
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
        print(f"  Findings: {len(rpt_res.get('findings', []))}, Abnormal Values: {len(rpt_res.get('abnormal_values', []))}")
    except Exception as e:
        results['ReportSummaryAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    # 7. CoordinatorAgent Test
    print("\n[TEST 7] CoordinatorAgent Full Pipeline Orchestration...")
    t0 = time.time()
    try:
        coord = CoordinatorAgent()
        c_res = coord.process({'text': 'I have had a high fever, chills, and persistent cough for 2 days.'})
        t1 = time.time()
        elapsed = t1 - t0
        agents_invoked = list(c_res.get('agent_results', {}).keys())
        passed = len(agents_invoked) >= 4 and len(c_res.get('response', '')) > 50
        results['CoordinatorAgent'] = {
            'status': 'PASS' if passed else 'FAIL',
            'time_seconds': round(elapsed, 4),
            'agents_orchestrated': agents_invoked,
            'response_length': len(c_res.get('response', ''))
        }
        print(f"  Result: {'PASS' if passed else 'FAIL'} in {elapsed:.4f}s")
        print(f"  Agents Orchestrated: {agents_invoked}")
        print(f"  Merged Response Length: {len(c_res.get('response', ''))} characters")
    except Exception as e:
        results['CoordinatorAgent'] = {'status': 'FAIL', 'error': str(e)}
        print(f"  FAILED with error: {e}")

    print("\n==================================================")
    print("             AGENT TEST SUMMARY")
    print("==================================================")
    all_passed = all(v.get('status') == 'PASS' for v in results.values())
    print(f"Overall Status: {'ALL PASS' if all_passed else 'SOME FAILED'}")
    for agent_name, r in results.items():
        print(f" - {agent_name}: {r['status']} ({r.get('time_seconds', 'N/A')}s)")

    # Save to json file
    output_path = os.path.join(os.path.dirname(__file__), 'agent_test_results.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

if __name__ == '__main__':
    run_agent_tests()
