# DATCOM Assistant: User Guide

This guide explains how to use the RAG system to get technical insights for UAV and fighter aircraft design, with a focus on DATCOM-related aerodynamic analysis.

## 1. Supported Design Areas

The system is an expert in five core design areas. When you ask a question, the agent first routes your query to the most relevant database.

-   **Aerodynamics**: For wing design, lift/drag analysis, wind tunnel data, and aerodynamic shapes.
-   **Avionics**: For flight control systems (FCS), radar, navigation, and avionics software architecture.
-   **Materials Science**: For composite materials, alloys, structural strength, and heat resistance.
-   **Weapons Integration**: For missile pylons, weapon loadouts, and electronic warfare systems.
-   **Propulsion**: For engine performance, thrust vectoring, and fuel systems.

## 2. How to Ask Questions

### Basic Queries

Use the `./query.sh` script for convenience. Ask direct, specific technical questions.

```bash
# Recommended method
./query.sh "What is the lift coefficient of an F-16 wing at Mach 0.9?"

# Direct invocation
python -m rag_system.query_rag_pg -q "What is the lift coefficient of an F-16 wing at Mach 0.9?"
```

### Specifying a Design Area

To bypass the automatic router and target a specific database, use the `--collection` flag.

```bash
./query.sh "Show me the code for the angle-of-attack limiter" --collection "Avionics"
```

### Interactive Mode

For a continuous session, start the interactive mode.

```bash
python -m rag_system.query_rag_pg --collection "Aerodynamics"

> What is the wave drag at supersonic speeds?
> Compare the lift-to-drag ratio of a delta wing vs. a trapezoidal wing.
> exit
```

## 3. Understanding the Agent's Workflow

The agent follows a two-step process:

1.  **Route**: First, it uses the `design_area_router` tool to analyze your question and select the most relevant design area (e.g., 'Avionics').
2.  **Retrieve**: Then, it uses the `retrieve_datcom_archive` tool to search for documents within that area and generates an answer based on the findings.

## 4. Best Practices for Effective Queries

To get the best results, follow these principles.

#### Be Specific and Technical

Use precise, technical terms and specific model numbers.

-   **Good**: "F-16 flight control system angle-of-attack limiter code."
-   **Bad**: "How does a plane fly?"

-   **Good**: "Tensile strength of carbon fiber composites at 800°C."
-   **Bad**: "What is the best material?"

#### Use Keywords

Include keywords that help the agent identify the correct domain and concepts.

-   **Aerodynamics**: `Lift Coefficient (CL)`, `Drag (CD)`, `Mach`, `Angle of Attack (AOA)`, `Thrust Vectoring`.
-   **Avionics**: `Flight Control System (FCS)`, `Kalman Filter`, `Radar Cross-Section (RCS)`.
-   **Models**: `F-16`, `F-35`, `Su-27`.

## 5. For Developers: Tool Implementation

The agent uses a suite of specialized tools to perform calculations and conversions related to DATCOM.

For detailed notes on the implementation, formulas, and design philosophy of these tools, see **[DATCOM Developer Notes](DATCOM_DEVELOPER_NOTES.md)**.
