from __future__ import annotations

import json
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class JobPostBenchmarkCase:
    case_id: str
    client_prompt: str
    expected_title_keywords: List[str]
    expected_skills: List[str]
    expected_budget_min: float
    expected_budget_max: float
    expected_duration: str


JOB_POST_BENCHMARKS: List[JobPostBenchmarkCase] = [
    JobPostBenchmarkCase(
        case_id="jp_01",
        client_prompt="Cần tuyển Lập trình viên Python FastAPI để xây dựng hệ thống RAG Chatbot với ChromaDB trong 2 tuần, ngân sách 500 GigCoins",
        expected_title_keywords=["python", "fastapi", "rag", "developer"],
        expected_skills=["Python", "FastAPI", "ChromaDB", "RAG", "REST API"],
        expected_budget_min=300.0,
        expected_budget_max=500.0,
        expected_duration="2 weeks"
    ),
    JobPostBenchmarkCase(
        case_id="jp_02",
        client_prompt="Need a React Native Mobile Developer to build cross-platform iOS and Android app with Redux and Firebase in 1 month, budget 800 - 1200 GC",
        expected_title_keywords=["react native", "mobile", "developer"],
        expected_skills=["React Native", "Redux", "Firebase", "TypeScript", "iOS", "Android"],
        expected_budget_min=800.0,
        expected_budget_max=1200.0,
        expected_duration="1 month"
    ),
    JobPostBenchmarkCase(
        case_id="jp_03",
        client_prompt="Need a Senior DevOps Engineer for AWS Cloud Infrastructure, Docker containerization, and GitHub Actions CI/CD pipeline setup in 3 weeks, budget 1000 GC",
        expected_title_keywords=["devops", "aws", "engineer"],
        expected_skills=["AWS", "Docker", "GitHub Actions", "CI/CD", "Kubernetes", "Terraform"],
        expected_budget_min=800.0,
        expected_budget_max=1000.0,
        expected_duration="3 weeks"
    ),
    JobPostBenchmarkCase(
        case_id="jp_04",
        client_prompt="Tuyển Lập trình viên Node.js Express & MongoDB làm backend REST API cho hệ thống thương mại điện tử trong 1 tháng, ngân sách 600 - 900 GigCoins",
        expected_title_keywords=["node.js", "backend", "developer"],
        expected_skills=["Node.js", "Express", "MongoDB", "REST API", "JavaScript"],
        expected_budget_min=600.0,
        expected_budget_max=900.0,
        expected_duration="1 month"
    ),
    JobPostBenchmarkCase(
        case_id="jp_05",
        client_prompt="Need a Senior UI/UX Designer to design mobile app wireframes and interactive prototypes in Figma for a fintech platform in 2 weeks, budget 400 - 700 GC",
        expected_title_keywords=["ui/ux", "designer", "figma"],
        expected_skills=["UI/UX Design", "Figma", "Wireframing", "Prototyping", "Mobile Design"],
        expected_budget_min=400.0,
        expected_budget_max=700.0,
        expected_duration="2 weeks"
    ),
    JobPostBenchmarkCase(
        case_id="jp_06",
        client_prompt="Tuyển Data Engineer làm hệ thống ETL Pipeline với Apache Spark và PostgreSQL trong 2 tháng, ngân sách 1500 GigCoins",
        expected_title_keywords=["data engineer", "etl", "spark"],
        expected_skills=["Python", "Apache Spark", "ETL", "PostgreSQL", "SQL"],
        expected_budget_min=1200.0,
        expected_budget_max=1500.0,
        expected_duration="2 months"
    ),
    JobPostBenchmarkCase(
        case_id="jp_07",
        client_prompt="Need a Cybersecurity Specialist to perform penetration testing and vulnerability assessment on web application in 1 week, budget 500 GC",
        expected_title_keywords=["cybersecurity", "penetration testing", "specialist"],
        expected_skills=["Cybersecurity", "Penetration Testing", "Vulnerability Assessment", "OWASP"],
        expected_budget_min=400.0,
        expected_budget_max=500.0,
        expected_duration="1 week"
    ),
    JobPostBenchmarkCase(
        case_id="jp_08",
        client_prompt="Tuyển Chuyên gia Cloud Architect thiết kế kiến trúc Microservices trên GCP Google Cloud Platform trong 1 tháng, ngân sách 2000 GigCoins",
        expected_title_keywords=["cloud architect", "gcp", "microservices"],
        expected_skills=["Google Cloud Platform", "Cloud Architecture", "Microservices", "Kubernetes"],
        expected_budget_min=1500.0,
        expected_budget_max=2000.0,
        expected_duration="1 month"
    ),
    JobPostBenchmarkCase(
        case_id="jp_09",
        client_prompt="Need a QA Automation Engineer to write Playwright E2E automation tests in TypeScript for web portal in 2 weeks, budget 600 GC",
        expected_title_keywords=["qa automation", "playwright", "engineer"],
        expected_skills=["QA Automation", "Playwright", "TypeScript", "E2E Testing", "Jest"],
        expected_budget_min=450.0,
        expected_budget_max=600.0,
        expected_duration="2 weeks"
    ),
    JobPostBenchmarkCase(
        case_id="jp_10",
        client_prompt="Tuyển Lập trình viên Golang làm gRPC high-throughput payment microservice trong 3 tuần, ngân sách 1000 - 1400 GigCoins",
        expected_title_keywords=["golang", "grpc", "developer"],
        expected_skills=["Golang", "gRPC", "Microservices", "Docker", "PostgreSQL"],
        expected_budget_min=1000.0,
        expected_budget_max=1400.0,
        expected_duration="3 weeks"
    ),
]


# Taxonomy lookup dictionaries
_taxonomy_loaded = False
majors_by_id: Dict[str, str] = {}
categories_by_id: Dict[str, str] = {}
skills_by_id: Dict[str, str] = {}


def load_taxonomy_if_needed():
    global _taxonomy_loaded, majors_by_id, categories_by_id, skills_by_id
    if _taxonomy_loaded:
        return
    
    # Locate categories_skills.jsonl
    base_dir = Path(__file__).parent.parent
    jsonl_path = base_dir / "knowledge-base" / "ai-create-job-post" / "categories_skills.jsonl"
    
    # Fallback to local execution directory if parent check is different
    if not jsonl_path.exists():
        jsonl_path = Path("knowledge-base/ai-create-job-post/categories_skills.jsonl")

    if jsonl_path.exists():
        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    type_val = item.get("type")
                    if type_val == "major":
                        majors_by_id[item["major_id"]] = item["name"]
                    elif type_val == "category":
                        categories_by_id[item["category_id"]] = item["name"]
                    elif type_val == "skill":
                        skills_by_id[item["skill_id"]] = item["name"]
            _taxonomy_loaded = True
        except Exception as e:
            print(f"Error loading taxonomy: {e}")


def evaluate_job_post_case(case: JobPostBenchmarkCase, ai_details: dict, ai_hiring_plan: dict) -> dict:
    """Evaluate generation fidelity metrics (Skill Recall, Precision, F1, Budget Clamping Faithfulness)."""
    load_taxonomy_if_needed()

    # Resolve system skill IDs to display names
    ai_resolved_skills = []
    system_skill_ids = ai_details.get("system_skill_ids") or []
    for sid in system_skill_ids:
        # Translate ID to display name if found, otherwise keep as is
        name = skills_by_id.get(sid, sid)
        ai_resolved_skills.append(name.lower())
    
    # Add custom skills directly (since they are generated as text)
    custom_skills = ai_details.get("custom_skills") or []
    for cs in custom_skills:
        ai_resolved_skills.append(cs.lower())

    ai_skills_raw = set(ai_resolved_skills)
    expected_skills_raw = set([s.lower() for s in case.expected_skills])

    # Compute Skill Recall & Precision
    matched_skills = set()
    for exp in expected_skills_raw:
        for ai_s in ai_skills_raw:
            if exp in ai_s or ai_s in exp:
                matched_skills.add(exp)
                break

    recall = len(matched_skills) / max(len(expected_skills_raw), 1)
    precision = len(matched_skills) / max(len(ai_skills_raw), 1)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Budget Clamping Faithfulness Check
    approved_budget = ai_details.get("budget_max") or ai_details.get("budget_min") or case.expected_budget_max
    milestones = ai_hiring_plan.get("milestones") or []
    milestone_sum = sum(m.get("amount", 0.0) for m in milestones) if milestones else 0.0
    budget_clamped_ok = abs(milestone_sum - approved_budget) < 0.05 if approved_budget > 0 else True

    # Title Keywords Check
    title_lower = (ai_details.get("title") or "").lower()
    title_match = any(kw.lower() in title_lower for kw in case.expected_title_keywords)

    return {
        "case_id": case.case_id,
        "skill_recall": round(recall * 100.0, 1),
        "skill_precision": round(precision * 100.0, 1),
        "f1_score": round(f1 * 100.0, 1),
        "title_match": title_match,
        "budget_clamped_ok": budget_clamped_ok,
        "approved_budget": approved_budget,
        "milestone_sum": milestone_sum,
        "vetting_questions_count": len(ai_hiring_plan.get("question_recruitment") or []),
    }
