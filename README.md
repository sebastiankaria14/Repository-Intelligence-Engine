# Repository Intelligence Engine (RIE)

Desktop Application for Local Codebase Intelligence, Architecture Discovery, and Security Auditing.

---

## Overview

Repository Intelligence Engine (RIE) is a standalone desktop application built on Electron, React, and TypeScript. It provides comprehensive static analysis, architectural visualization, and security auditing for local software repositories. 

RIE operates entirely offline on your machine. It requires zero external API keys, zero cloud subscriptions, and zero external network calls. All code intelligence is generated locally using deterministic Abstract Syntax Tree (AST) analysis, call graph modeling, graph centrality algorithms, and static security heuristics.

---

## Key Features

- **Architecture Discovery**: Automatically identifies architectural patterns (MVC, Layered, Hexagonal, Microservices, Modular Monolith) and maps cross-module communication flows.
- **API and Endpoint Discovery**: Detects REST, GraphQL, and RPC endpoints, extracting HTTP methods, routes, parameters, and handler bindings.
- **Dependency and Impact Analysis**: Maps internal and external dependencies, identifying circular references, coupling bottlenecks, and architectural blast radius.
- **Security Audit and Vulnerability Detection**: Scans for OWASP Top 10 vulnerabilities, insecure direct object references, dangerous input sinks, and high-entropy hardcoded secrets.
- **Performance and Code Health**: Evaluates cognitive and cyclomatic complexity, dead code, duplicated logic, and N+1 query antipatterns.
- **Git and History Intelligence**: Computes file churn, hotspot files, code ownership metrics, and author contribution distributions.
- **Local Intelligence Console**: Interactive inspection of codebase components and symbol relationships powered by local graph reasoning.

---

## How It Works

1. **Repository Selection**: Select any local folder or cloned repository using the native desktop file picker.
2. **AST Parsing and Symbol Extraction**: Language-specific parsers analyze source files to extract functions, classes, interfaces, import statements, and function calls.
3. **Graph Construction**: The analysis engine constructs an in-memory knowledge graph representing dependencies, file hierarchies, and symbol calls.
4. **Algorithmic Analysis**:
   - **Centrality Analysis**: PageRank algorithms evaluate structural hubs and single points of failure.
   - **Cycle Detection**: Graph traversal algorithms pinpoint circular dependency loops.
   - **Heuristic Pattern Matching**: Static rule engines detect security flaws and architectural antipatterns.
5. **Interactive Visualization**: The Electron renderer displays interactive dependency graphs, metrics cards, and filtered vulnerability tables with smooth animations.

---

## Technology Stack

- **Desktop Shell**: Electron
- **User Interface**: React, TypeScript, Vite, Tailwind CSS
- **Visualization**: React Flow, Cytoscape.js, Recharts
- **Icons**: Lucide Icons (clean SVG icons, zero emojis)
- **Analysis Engine**: Python / Node AST engines, Tree-sitter, NetworkX
- **Local Storage**: Embedded SQLite

---

## Quick Start (Development)

### Prerequisites

- Node.js (v20+)
- Python (3.11+)
- Git

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd repository-intelligence-engine

# 2. Install dependencies
npm install

# 3. Launch the desktop application
npm run dev
```

---

## Phased Project Architecture

- **Phase 1: Housekeeping and Cleanup**: Removal of legacy Docker containers, obsolete configs, and unused scratch files.
- **Phase 2: Electron Desktop Foundation**: Native desktop window, preload context bridge, and local filesystem integration.
- **Phase 3: User Interface Redesign**: Modern dark-mode interface with borderless buttons, fluid animations, and zero emojis.
- **Phase 4: Local Intelligence Engine**: AST parsing, in-memory graph modeling, and rule-based security analyzers requiring zero API keys.
- **Phase 5: IPC and Pipeline Integration**: Asynchronous progress streaming between the Electron shell and the local analysis engine.
- **Phase 6: Verification and Packaging**: Standalone cross-platform desktop installer production.

---

## License

MIT License.
