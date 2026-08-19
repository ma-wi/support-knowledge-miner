# Cluster-Keywords, LLM-Taxonomie und fixierte Cluster

- Requirement ID: chg-007-cluster-taxonomy-and-fixed-clusters
- Status: accepted
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

Cluster sind ohne charakteristische Begriffe schwer vergleichbar. Die vorhandene
Summary-Erzeugung kennt nur Beispiele, und bestehende Verfeinerungen können weder
redundante Cluster anhand ihrer fachlichen Summaries konsolidieren noch Nachrichten
gegen eine vorhandene Taxonomie neu zuordnen. Fachlich abgeschlossene Cluster
werden bei jeder Verfeinerung erneut verarbeitet.

## Desired outcome

Jedes erzeugte Cluster besitzt persistierte typische Keywords. Summaries verwenden
diese Keywords zusätzlich zu den Stichproben. Zwei LLM-basierte Algorithmen können
eine vorhandene Cluster-Taxonomie konsolidieren beziehungsweise Supportpaare gegen
eine vorhandene Taxonomie zuordnen. Fixierte Cluster werden in Child-Sets
unverändert übernommen und nie erneut geclustert.

## Scope

In scope:

- konfigurierbar 1 bis 50 c-TF-IDF-Keywords je Cluster, Standard 10;
- Anzeige und Suche der Keywords im Explorer;
- Keywords als zusätzlicher Kontext im Cluster-Summary-Prompt;
- Algorithmus `llm_taxonomy` zur nicht-redundanten Konsolidierung vollständiger
  Cluster-Summaries in hierarchische Kategoriepfade;
- Algorithmus `llm_assignment` zur Zuordnung aller ausgewählten aktiven
  Supportpaare gegen die vollständige aktive Parent-Taxonomie;
- validierte LLM-Rückgaben mit stabilen Quell-Cluster- beziehungsweise
  Nachrichtenpaar-IDs;
- ein gemeinsamer Ausreißercluster für fachlich nicht passende LLM-Zuordnungen;
- Status `fixed` und unveränderte Übernahme fixierter Cluster in Child-Sets;
- unveränderte Übernahme aktiver Parent-Ausreißer bei Taxonomie-Reduktion, ohne
  diese an das LLM zu senden;
- bestehende lokale Ollama- und explizit bestätigte OpenAI-Verwendung.

Out of scope:

- manuelles Verschieben einzelner Memberships;
- eine neue Taxonomie-Seite oder ein eigener Baumeditor;
- automatische fachliche Freigabe von LLM-Inhalten;
- andere externe Provider oder Produktionszugriffe.

## Accepted decisions

- Keywords folgen der gewählten Textbasis: Kundenanfrage, Supportantwort oder
  kombinierter Text.
- Keywords werden nach jedem echten Clustering neu berechnet. Bei unverändert
  übernommenen fixierten oder Ausreißer-Clustern bleiben sie unverändert.
- Taxonomie-Hierarchie wird als nicht-leerer `category_path` je Zielcluster
  gespeichert und im bestehenden Kategoriefeld als ` > `-Pfad dargestellt.
- `llm_taxonomy` erhält alle ausgewählten aktiven, nicht fixierten und nicht als
  Ausreißer markierten Parent-Cluster. Jeder Quellcluster muss exakt einem
  Zielcluster zugeordnet sein; unbekannte, doppelte oder fehlende IDs lassen den
  Job sicher fehlschlagen.
- `llm_assignment` erhält die vollständige aktive, nicht fixierte Parent-Taxonomie
  und begrenzte Batches ausgewählter Supportpaare. Jede Paar-ID muss exakt einmal
  einem bekannten Taxonomiecluster oder `outlier` zugeordnet sein.
- Fixierte Parent-Cluster werden unabhängig von der sichtbaren Quellauswahl in
  jedes Refinement-Child übernommen. Ihre Clusterfelder und Memberships werden
  kopiert; ihre Mitglieder werden aus dem neuen Algorithmus-Input entfernt.
- LLM-Algorithmen benötigen einen konfigurierten LLM-Provider und ein Modell.
- Die vorhandene Cluster-Set-POST- und Job-Pipeline bleibt Owner; es entstehen
  keine parallelen Endpunkte oder Worker.

## Acceptance criteria

- [x] AC-1: Cluster-Set-Erzeugung akzeptiert eine Keyword-Anzahl von 1 bis 50,
  verwendet standardmäßig 10 und lehnt andere Werte ohne Schreibzugriff ab.
- [x] AC-2: Nach HDBSCAN, Agglomerative und den beiden LLM-Algorithmen besitzt jedes
  neu gebildete Cluster bis zu n persistierte, deterministisch geordnete Keywords.
- [x] AC-3: Explorer-Zeilen zeigen Keywords an und die Textsuche berücksichtigt sie.
- [x] AC-4: Der Summary-Prompt enthält die persistierten Keywords zusätzlich zu den
  ausgewählten Beispielen; Summary-Neuerstellung nutzt dieselben Keywords.
- [x] AC-5: `llm_taxonomy` sendet vollständige Summary-Felder, Keywords und stabile
  Cluster-IDs, validiert eine vollständige überschneidungsfreie Rückzuordnung und
  vereinigt Memberships in den neuen hierarchischen Zielclustern.
- [x] AC-6: `llm_taxonomy` sendet Ausreißer und fixierte Cluster nicht an das LLM,
  übernimmt sie aber unverändert in das Child-Set.
- [x] AC-7: `llm_assignment` sendet die vollständige aktive Parent-Taxonomie und
  begrenzte Supportpaar-Batches entsprechend der gewählten Textbasis; jede gültige
  Antwort erzeugt genau eine Membership je Eingabepaar.
- [x] AC-8: `llm_assignment` legt fachlich nicht passende Paare in einem gemeinsamen
  Ausreißercluster ab und lehnt unvollständige oder unbekannte LLM-IDs sicher ab.
- [x] AC-9: Der Explorer kann Cluster auf `fixed` setzen. Jedes Refinement-Child
  übernimmt alle fixierten Parent-Cluster samt Feldern, Keywords und Memberships
  unverändert und entfernt deren Mitglieder aus dem Clustering-Input.
- [x] AC-10: OpenAI überträgt Originaltexte oder Summaries nur nach expliziter
  Bestätigung; Prompts, Antworten, Aufrufzahl und Ressourcen bleiben begrenzt.
- [x] AC-11: API, Migration, Fehlervertrag, Frontend, Export und Dokumentation
  beschreiben denselben aktuellen Zustand; bestehende Cluster-Sets bleiben lesbar.
- [x] AC-12: Backend-, API-, Migrations- und Frontendtests decken Erfolgs-,
  Validierungs-, Provider-, fehlerhafte LLM-Ausgabe-, Fixed- und Ausreißerpfade ab.
