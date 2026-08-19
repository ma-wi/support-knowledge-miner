# LLM-Assignment ohne künstliches Datensatzlimit

- Requirement ID: chg-011-unbounded-llm-assignment
- Status: implemented
- Ready for implementation: yes
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

`llm_assignment` verwirft einen ansonsten zulässigen Refinement-Job bereits bei
mehr als 10.000 ausgewählten Supportpaaren mit `CLUSTER_BUDGET_EXCEEDED`. Diese
Grenze ist unabhängig von Modell, Taxonomie und der bereits vorhandenen gebatchten
Verarbeitung. Der konkret fehlgeschlagene lokale Job enthält 23.801 Paare bei nur
41 effektiven Taxonomieclustern; sein erster 20er-Batch umfasst 32.988 Promptzeichen.

## Desired outcome

Alle im unveränderlichen Child-Snapshot ausgewählten Paare werden vom
LLM-Assignment in den bestehenden kleinen, gebundenen Batches verarbeitet. Es gibt
kein zusätzliches Assignment-Gesamtpaarlimit. Die bereits vorgelagerte gebundene
Datensatz-/Cluster-Set-Erstellung, die Batchgröße, Provider-Payloadgrenzen,
Cancellation und atomare Persistenz bleiben erhalten.

## Acceptance criteria

- [x] AC-1: `llm_assignment` lehnt 23.801 oder mehr zulässig ausgewählte Paare nicht
  wegen eines eigenständigen Assignment-Gesamtpaarlimits ab.
- [x] AC-2: Provideraufrufe bleiben auf höchstens 20 Paare pro Request begrenzt und
  jeder ausgewählte Paar-Identifier wird genau einmal verarbeitet.
- [x] AC-3: Provider-/Parserfehler und Cancellation persistieren weiterhin keine
  partiellen Assignment-Cluster.
- [x] AC-4: Taxonomie-Softlimits aus den Projekteinstellungen gelten weiterhin nur
  für `llm_taxonomy`, nicht für `llm_assignment`.
- [x] AC-5: API, UI und Persistenzschema bleiben kompatibel; der irreführende
  Budgetfehler tritt für das entfernte Assignment-Limit nicht mehr auf.
- [x] AC-6: Fokussierte Tests, vollständige Verifikation und unabhängiger
  Code-/Security-Review sind grün.
