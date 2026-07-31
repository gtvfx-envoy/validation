# Filesystem Pack Plan

## Purpose
This pack supports Week 2 through Week 3 of the course by providing a clean and flawed project tree that can be scanned by validation scripts. It is intentionally small, believable, and built to support progressive teaching.

## Project Theme
The example project is `project_aurora`.

## Teaching Goals
- Show directory traversal and filesystem scanning
- Demonstrate naming validation
- Demonstrate extension allowlists
- Demonstrate banned-term checks
- Demonstrate empty-file detection
- Demonstrate folder-policy validation
- Support structured reporting in later sessions

## Design Principles
- Keep examples believable and production-adjacent
- Keep failures intentional and easy to explain
- Separate clean and flawed examples for easy comparison
- Reuse the same content for A2 and A3

## Primary Support
- Week 2 Session 03: filesystem-based validation
- Week 2 Session 04: rule abstraction and configurable systems
- Week 3 Session 05: scalable validation framework
- Week 3 Session 06: plugin-style rule discovery

## Recommended Initial Rule Set
1. File name must match approved pattern
2. File extension must be allowed
3. File must not be empty
4. Paths must not contain forbidden folder names
5. Names must not contain banned terms
6. File must live in an approved category path
