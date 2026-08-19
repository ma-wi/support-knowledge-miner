# Flache und konservative LLM-Taxonomie

- Requirement ID: chg-014-flat-conservative-llm-taxonomy
- Status: implemented
- Ready for implementation: yes
- Decision owner: mawi
- Last updated: 2026-08-16

## Problem

`llm_taxonomy` erzeugt feinteilige Kategorienhierarchien und führt fachlich
eigenständige Titel zu aggressiv zusammen. Dadurch werden grobe Kategorien wie
„Reparatur“ zu Pfaden wie „Akkudiagnose > Fehlerbilder“, während wichtige Anliegen
wie „Versand ins Ausland“ als eigener Titel verschwinden.

## Desired outcome

Kategorien bleiben eine konsistente, grobe Ebene aus dem Parent-Cluster-Set.
Produkt-, Marken-, Modell- und Detailbegriffe gehören in die Titel. Die Reduktion
führt nur redundante Titel mit demselben Anliegen und Supportprozess zusammen;
eigenständige oder unsichere Fälle bleiben getrennt.

## Acceptance criteria

- [x] AC-1: Aus den Parent-Kategorien wird ein flaches kanonisches Vokabular
  gebildet; speziellere Varianten wie „Akkureparatur“ werden bei vorhandenem
  „Reparatur“ nicht als eigene erlaubte Kategorie angeboten.
- [x] AC-2: Das Structured-Output-Schema erlaubt genau eine Kategorieebene und nur
  Werte aus dem kanonischen Parent-Vokabular.
- [x] AC-3: Prompt und Beispiele verbieten neue Kategorien und Hierarchien und
  ordnen Marken, Modelle, Bauteile, Fehlerbilder und weitere Details den Titeln zu.
- [x] AC-4: Der Prompt reduziert konservativ: nur gleiches Anliegen und gleicher
  Supportprozess werden zusammengeführt; im Zweifel bleiben Cluster getrennt und
  seltene eigenständige Anliegen erhalten.
- [x] AC-5: Beispiele decken Akkuvarianten, Zellentausch und die getrennte Erhaltung
  von „Versand ins Ausland“, Versandstatus und Versandkosten ab.
- [x] AC-6: Die Backendvalidierung weist mehrstufige oder unbekannte Kategorien auch
  bei einem schemauntreuen Provider sicher ab; die exakte Quellpartition und
  atomare Persistenz bleiben bestehen.
- [x] AC-7: Fokussierte Tests, Full Verify und unabhängiger Code-/Security-Review
  sind grün.
