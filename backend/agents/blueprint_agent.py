"""
Startup Blueprint Agent - Orchestrates all blueprint generation modules.
"""
import logging
from typing import Optional

from rag.rag_engine import get_rag_engine
from rag.granite_client import get_granite_client

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Prompt templates for each blueprint section
# ─────────────────────────────────────────────

SECTION_PROMPTS = {
    "executive_summary": """You are an expert startup consultant. Using the context below and the startup idea provided, write a concise executive summary (3-4 paragraphs) covering:
- The problem being solved
- The proposed solution and its uniqueness
- Target market and opportunity size
- The team's competitive advantage

Context from startup knowledge base:
{context}

Startup Idea: {idea}

Executive Summary:""",

    "business_model_canvas": """You are a business strategy expert. Based on the startup idea and context below, generate a detailed Business Model Canvas with these 9 sections. For each section, provide 3-5 specific, actionable points.

Context:
{context}

Startup Idea: {idea}

Generate the Business Model Canvas:

1. KEY PARTNERS:
2. KEY ACTIVITIES:
3. KEY RESOURCES:
4. VALUE PROPOSITIONS:
5. CUSTOMER RELATIONSHIPS:
6. CHANNELS:
7. CUSTOMER SEGMENTS:
8. COST STRUCTURE:
9. REVENUE STREAMS:""",

    "market_analysis": """You are a market research analyst. Based on the context and startup idea, provide a comprehensive market analysis including:
1. TAM (Total Addressable Market) with estimated size
2. SAM (Serviceable Addressable Market)
3. SOM (Serviceable Obtainable Market for 3 years)
4. Key market trends driving growth
5. Top 3-5 competitors with their strengths/weaknesses
6. Market entry barriers and how to overcome them

Context:
{context}

Startup Idea: {idea}

Market Analysis:""",

    "revenue_model": """You are a financial strategist. Based on the startup idea and context, recommend:
1. The most suitable revenue model(s) and why
2. Pricing strategy with specific price points
3. Projected revenue milestones (Year 1, Year 2, Year 3)
4. Key revenue metrics to track (MRR, ARR, LTV, CAC)
5. Path to profitability

Context:
{context}

Startup Idea: {idea}

Revenue Model Recommendation:""",

    "estimated_budget": """You are a startup CFO. Based on the startup idea and context, create an estimated startup budget covering:
1. Initial Setup Costs (one-time)
2. Monthly Operational Costs (recurring)
3. Technology & Infrastructure Costs
4. Marketing & Customer Acquisition Budget
5. Team Hiring Plan with salary estimates
6. Total Runway needed (in months) for Seed stage
7. Recommended funding amount to raise

Context:
{context}

Startup Idea: {idea}

Estimated Budget Breakdown:""",

    "go_to_market": """You are a growth marketing expert. Create a detailed Go-To-Market strategy for this startup:
1. Target Customer Profile (ICP) - specific demographics/firmographics
2. Value Proposition Statement
3. Top 3 customer acquisition channels with tactics
4. Launch strategy (soft launch → full launch milestones)
5. First 100 customer acquisition plan
6. Key partnerships to pursue
7. 90-day action plan post-launch

Context:
{context}

Startup Idea: {idea}

Go-To-Market Strategy:""",

    "funding_roadmap": """You are a venture capital advisor. Based on the startup idea and context, provide:
1. Recommended funding stage to start at and why
2. Top 5 relevant investors/funds to approach (with focus areas)
3. Relevant government schemes and grants to apply for
4. Top 3 accelerators/incubators to apply for
5. Valuation benchmarks for each funding stage
6. Fundraising timeline and milestones to hit before each raise
7. Key documents to prepare for investor outreach

Context:
{context}

Startup Idea: {idea}

Funding Roadmap:""",

    "legal_compliance": """You are a startup legal advisor. Based on the startup idea and context, provide:
1. Recommended business entity structure and why
2. Essential legal documents to create immediately
3. Intellectual property strategy (patents, trademarks, copyrights)
4. Industry-specific regulatory requirements and licenses
5. Data privacy and compliance requirements (GDPR, PDPB, HIPAA, etc.)
6. Key compliance deadlines and calendar
7. Estimated legal costs and where to save money

Context:
{context}

Startup Idea: {idea}

Legal & Compliance Roadmap:""",

    "tech_stack": """You are a CTO and technical architect. Based on the startup idea, recommend:
1. Recommended technology stack (frontend, backend, database, cloud)
2. Why IBM Cloud / IBM watsonx services should be integrated (mandatory requirement)
3. MVP feature list (minimum viable product - only essentials)
4. System architecture overview
5. Third-party APIs and integrations needed
6. Security and scalability considerations
7. Technical team composition needed
8. Estimated time to MVP (in weeks)

Context:
{context}

Startup Idea: {idea}

Technology Stack Recommendation:""",
}

COMBINED_PROMPT = """You are an expert startup consultant and business strategist. A user has described their startup idea. Using the retrieved knowledge base context below, generate a complete Startup Blueprint.

Startup Idea: {idea}

Retrieved Knowledge Base Context:
{context}

Generate a COMPLETE and DETAILED Startup Blueprint covering all sections below. Be specific, actionable, and realistic.

=== STARTUP BLUEPRINT ===

## 1. EXECUTIVE SUMMARY
[Provide 3-4 paragraphs covering the problem, solution, market opportunity, and competitive advantage]

## 2. BUSINESS MODEL CANVAS
KEY PARTNERS: [List 3-5 key partners]
KEY ACTIVITIES: [List 3-5 key activities]
KEY RESOURCES: [List 3-5 key resources]
VALUE PROPOSITIONS: [List 3-5 value propositions]
CUSTOMER RELATIONSHIPS: [List 3-5 customer relationship types]
CHANNELS: [List 3-5 distribution channels]
CUSTOMER SEGMENTS: [Describe 2-3 customer segments]
COST STRUCTURE: [List major costs]
REVENUE STREAMS: [List revenue streams with estimates]

## 3. MARKET ANALYSIS
[TAM/SAM/SOM, market trends, top competitors, barriers to entry]

## 4. REVENUE MODEL
[Recommended revenue model, pricing strategy, Year 1/2/3 projections]

## 5. ESTIMATED BUDGET
[Setup costs, monthly burn, team plan, total funding needed]

## 6. GO-TO-MARKET STRATEGY
[ICP, acquisition channels, launch plan, first 100 customers]

## 7. FUNDING ROADMAP
[Funding stages, top investors, government schemes, accelerators]

## 8. LEGAL & COMPLIANCE
[Entity structure, key legal docs, IP strategy, regulatory requirements]

## 9. TECHNOLOGY STACK
[Tech stack including IBM Cloud/watsonx, MVP features, architecture]

## 10. 90-DAY ACTION PLAN
[Week-by-week milestones for the first 90 days]

Blueprint:"""


class BlueprintAgent:
    """Orchestrates the startup blueprint generation using RAG + IBM Granite."""

    def __init__(self):
        self.rag = get_rag_engine()
        self.llm = get_granite_client()

    def _build_context(self, idea: str, section_keywords: Optional[str] = None) -> str:
        """Retrieve relevant context from the knowledge base."""
        query = section_keywords or idea
        return self.rag.get_context_for_query(query, n_results=8)

    def generate_full_blueprint(self, idea: str) -> dict:
        """
        Generate a complete startup blueprint for the given idea.
        Returns a structured dict with all sections.
        """
        logger.info("Generating full blueprint for idea: %s", idea[:100])

        # Build comprehensive context combining multiple queries
        queries = [
            f"{idea} funding investors",
            f"{idea} market analysis competitors",
            f"{idea} revenue model business",
            f"{idea} legal compliance requirements",
            f"{idea} go to market strategy",
        ]

        all_contexts = []
        for q in queries:
            chunks = self.rag.retrieve(q, n_results=3)
            for doc, source, _ in chunks:
                all_contexts.append(f"[{source}]\n{doc}")

        # Deduplicate while preserving order
        seen = set()
        unique_contexts = []
        for ctx in all_contexts:
            if ctx not in seen:
                seen.add(ctx)
                unique_contexts.append(ctx)

        combined_context = "\n\n---\n\n".join(unique_contexts[:10])

        prompt = COMBINED_PROMPT.format(idea=idea, context=combined_context)

        raw_output = self.llm.generate(prompt)

        # Parse the raw output into sections
        sections = self._parse_blueprint_sections(raw_output)

        return {
            "idea": idea,
            "raw_blueprint": raw_output,
            "sections": sections,
        }

    def generate_section(self, idea: str, section_name: str) -> str:
        """Generate a specific section of the blueprint."""
        if section_name not in SECTION_PROMPTS:
            raise ValueError(f"Unknown section: {section_name}. Valid: {list(SECTION_PROMPTS.keys())}")

        section_context_map = {
            "executive_summary": idea,
            "business_model_canvas": f"{idea} business model revenue",
            "market_analysis": f"{idea} market size competitors trends",
            "revenue_model": f"{idea} revenue pricing monetization",
            "estimated_budget": f"{idea} startup costs budget team",
            "go_to_market": f"{idea} marketing customers acquisition launch",
            "funding_roadmap": f"{idea} funding investors venture capital grants",
            "legal_compliance": f"{idea} legal compliance regulations incorporation",
            "tech_stack": f"{idea} technology platform infrastructure IBM Cloud",
        }

        context_query = section_context_map.get(section_name, idea)
        context = self._build_context(idea, context_query)
        prompt = SECTION_PROMPTS[section_name].format(idea=idea, context=context)

        return self.llm.generate(prompt)

    def _parse_blueprint_sections(self, raw_text: str) -> dict:
        """Parse the raw blueprint text into structured sections."""
        section_markers = {
            "executive_summary": ["## 1. EXECUTIVE SUMMARY", "## 1."],
            "business_model_canvas": ["## 2. BUSINESS MODEL CANVAS", "## 2."],
            "market_analysis": ["## 3. MARKET ANALYSIS", "## 3."],
            "revenue_model": ["## 4. REVENUE MODEL", "## 4."],
            "estimated_budget": ["## 5. ESTIMATED BUDGET", "## 5."],
            "go_to_market": ["## 6. GO-TO-MARKET STRATEGY", "## 6."],
            "funding_roadmap": ["## 7. FUNDING ROADMAP", "## 7."],
            "legal_compliance": ["## 8. LEGAL & COMPLIANCE", "## 8."],
            "tech_stack": ["## 9. TECHNOLOGY STACK", "## 9."],
            "action_plan": ["## 10. 90-DAY ACTION PLAN", "## 10."],
        }

        sections = {}
        lines = raw_text.split("\n")

        current_section = None
        current_content = []

        for line in lines:
            found_section = None
            for section_key, markers in section_markers.items():
                for marker in markers:
                    if line.strip().startswith(marker):
                        found_section = section_key
                        break
                if found_section:
                    break

            if found_section:
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = found_section
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save the last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()

        # If parsing failed, return the whole raw text under a single key
        if not sections:
            sections["full_blueprint"] = raw_text

        return sections


# Singleton
_blueprint_agent: Optional[BlueprintAgent] = None


def get_blueprint_agent() -> BlueprintAgent:
    global _blueprint_agent
    if _blueprint_agent is None:
        _blueprint_agent = BlueprintAgent()
    return _blueprint_agent
