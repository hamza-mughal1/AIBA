# Developer Guidelines & Code Rules

## 1. Core Philosophy
* **Product-Grade Quality:** Deliver clean, optimized, production-ready code that adheres to industry best practices.
* **Simplicity > Cleverness:** Prioritize clear, explicit, and maintainable logic over complex, dense shorthand or confusing one-liners.

## 2. Architecture & Design
* **Single Responsibility:** Create a dedicated, focused function for each distinct task.
* **Smart Abstraction:** Only abstract logic into private/helper functions if that exact logic is actively shared across *multiple* functions. Avoid over-engineering.
* **Minimalist Footprint:** Write exactly what is required to satisfy the objective. Do not bloat the codebase with unnecessary features or speculative code.
* **Optimization:** Write as optimized logic as possible, try to not use n+1 queries as much as possible, try to use caching, batching, and pre-fetch.

## 3. Code Style & Readability
* **Explicit Logic:** Do not use overly complex expressions, deeply nested ternaries, or dense one-liner hacks. Code must be easily scannable and understandable.
* **Concise Documentation:** Do not write large blocks of comments. Write comments *only* when strictly necessary to explain complex "why" logic, keeping them brief, punchy, and meaningful.

## 4. Quality Assurance & Communication
* **Zero-Bug Tolerance:** All code will undergo rigorous senior developer review. Thoroughly think through edge cases and error handling.
* **Clarify Over Guessing:** If requirements are ambiguous, ask clarifying questions instead of making assumptions.

## 5. Initialization & Code Execution
* **UV:** Use UV with python to execute and manage environment and project.
