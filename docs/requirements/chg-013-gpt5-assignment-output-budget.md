# Modellgerechtes GPT-5-Assignment-Ausgabebudget

- Requirement ID: chg-013-gpt5-assignment-output-budget
- Status: implemented
- Ready for implementation: yes
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

`llm_assignment` fordert unabhängig vom gewählten Modell höchstens 4.000
Ausgabetokens an. OpenAI-GPT-5-Modelle verbrauchen innerhalb dieses Budgets auch
Reasoning-Tokens und können deshalb ohne fertige strukturierte Antwort mit
`max_output_tokens` abbrechen. Der Hintergrundjob meldet dann irreführend nur den
allgemeinen Fehler `LLM_PROVIDER_UNAVAILABLE`.

## Desired outcome

Assignment-Aufrufe verwenden für OpenAI-Modelle der GPT-5-Familie die bereits
vorhandene, hart begrenzte 128.000-Token-Providerfreigabe. Andere Provider und
Modellfamilien behalten das bisherige 4.000-Token-Assignmentbudget. Sichere
Providerdiagnosen sind über die Cluster-Set-ID dem auslösenden Job zugeordnet;
Prompt- oder Antwortinhalte werden nicht protokolliert.

## Acceptance criteria

- [x] AC-1: `llm_assignment` fordert für `OpenAI/gpt-5-mini` 128.000
  Ausgabetokens an und scheitert nicht mehr aufgrund des bisherigen lokalen
  4.000-Token-Sonderlimits.
- [x] AC-2: Die GPT-5-Erkennung akzeptiert nur die echte Modellfamiliengrenze;
  ähnlich benannte Modelle und andere Provider behalten 4.000 Tokens.
- [x] AC-3: Jeder Assignment-Provideraufruf erhält die validierte Cluster-Set-ID
  als Diagnosekorrelation.
- [x] AC-4: Sichere Assignment-Request-/Response-Diagnostik enthält nur Metadaten
  und Größen, niemals Supportinhalte, Prompts, Antworten oder vollständige ID-Listen.
- [x] AC-5: Batching, semantische Antwortreparatur, atomare Persistenz,
  Abbruchverhalten und bestehende Fehlercodes bleiben unverändert.
- [x] AC-6: Fokussierte Tests, Full Verify und unabhängiger Code-/Security-Review
  sind grün.
