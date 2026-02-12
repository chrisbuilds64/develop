# Agent Spec Template

## Meta
- **ID:** AG-XXX
- **Name:** [Agent Name]
- **Version:** 1.0
- **Author:** [Wer hat die Spec geschrieben]
- **Status:** DRAFT | ACTIVE | DEPRECATED

## Role
[1-2 Saetze: Wer ist dieser Agent? Welche Expertise hat er?]

## Goal
[Was soll am Ende rauskommen? Messbares Ergebnis.]

## Input
- **Trigger:** [Wie wird der Agent gestartet? Manuell, Cron, API Call, Event?]
- **Required:** [Was muss er bekommen? Parameter, Daten]
- **Optional:** [Zusaetzliche Inputs die er verarbeiten kann]

## Output
- **Format:** [Structured Text, JSON, Markdown, etc.]
- **Delivery:** [Terminal, File, API Response, Telegram, etc.]
- **Structure:** [Beschreibung der Output-Struktur]

## Tools
[Welche Werkzeuge braucht der Agent? Pro Tool:]

### Tool: [tool_name]
- **Purpose:** Was tut es?
- **Input:** Was bekommt es?
- **Output:** Was liefert es?
- **Access:** Read-only / Read-write / External API

## Rules
### Must Do
- [Pflicht-Verhalten]

### Must Not Do
- [Verbotenes Verhalten]

### Quality Criteria
- [Woran messen wir ob der Agent gut arbeitet?]

## Context
[Hintergrundwissen das der Agent braucht. Domain Knowledge, Brand Info, etc.]

## Examples
### Good Output (Beispiel)
[Wie sieht ein gutes Ergebnis aus?]

### Bad Output (Anti-Beispiel)
[Was wollen wir NICHT sehen?]
