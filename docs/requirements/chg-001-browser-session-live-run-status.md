# Requirement: Browser-Sitzung und laufend aktualisierte Analyse-Runs

- Requirement ID: CHG-001
- Work type: incremental-change
- Affected capability specifications:
  `docs/specifications/support-knowledge-miner-mvp1.md`

## Problem

Ein Seiten-Reload verwirft den nur im React-Arbeitsspeicher gehaltenen Login, obwohl
die serverseitige Sitzung weiterhin gültig ist. Außerdem lädt die Projektansicht
Analyse-Runs nur beim Öffnen eines Projekts oder nach lokalen Aktionen; Fortschritt
und Status eines Hintergrund-Runs bleiben deshalb bis zu einem Seiten-Reload
veraltet.

## Desired outcome

Eine gültige Anmeldung übersteht Reloads innerhalb desselben Browser-Tabs. Die
Run-Ansicht zeigt den serverseitig aktuellen Stand eines Projekts ohne manuellen
Reload in einem kurzen, vorhersehbaren Aktualisierungsintervall.

## Users and stakeholders

- Angemeldete Analysten und Kuratoren.
- Decision owner: anfordernder Product Owner (Conversation User; Name nicht
  angegeben).
- Security reviewer for browser token handling and session invalidation.

## Optional user stories or journey scenarios

- US-1: Als angemeldeter Nutzer möchte ich die Seite aktualisieren können, ohne mich
  erneut anzumelden, solange meine Browser- und Serversitzung gültig ist.
- US-2: Als Nutzer eines laufenden Analyse-Runs möchte ich Status und Fortschritt in
  der Runs-Ansicht automatisch aktuell sehen.

## Functional requirements

- FR-1: Das Frontend bewahrt ausschließlich das Bearer-Token in tabgebundenem
  Browser-Sitzungsspeicher auf.
- FR-2: Beim App-Start validiert das Frontend ein vorhandenes Token über
  `GET /api/auth/me`, bevor geschützte Inhalte angezeigt werden, und bezieht die
  Benutzeridentität ausschließlich aus dieser Serverantwort.
- FR-3: Fehlendes, ungültiges, abgelaufenes oder widerrufenes Sitzungstoken führt in
  den nicht angemeldeten Zustand und wird aus dem Browser-Sitzungsspeicher entfernt.
- FR-4: Explizite Abmeldung verwendet den bestehenden
  `POST /api/auth/sign-out`-Endpunkt und entfernt den lokalen Sitzungseintrag auch,
  wenn das Backend nicht erreichbar ist.
- FR-5: Die Runs-Ansicht lädt beim Öffnen sofort die Run-Liste des aktuellen Projekts
  und aktualisiert sie anschließend alle zwei Sekunden, solange die Ansicht sichtbar
  und aktiv ist.
- FR-6: Es darf je Ansicht höchstens eine Polling-Anfrage gleichzeitig aktiv sein.
  Antworten eines zuvor geöffneten Projekts, einer abgemeldeten Sitzung oder einer
  verlassenen Runs-Ansicht dürfen den aktuellen Zustand nicht überschreiben.
- FR-7: Beim Verlassen der Runs-Ansicht, Projektwechsel, Logout, Unmount oder
  unsichtbarem Dokument endet das Polling; beim Zurückkehren erfolgt sofort eine
  Aktualisierung.
- FR-8: Polling-Fehler behalten den letzten erfolgreichen Run-Stand bei und lösen
  keine überlappende Retry-Schleife aus. Eine ungültige Sitzung wird nach dem
  bestehenden Authentifizierungsvertrag behandelt.

## Non-functional requirements

- Security: Kein Passwort und kein Benutzerobjekt wird im Browser-Sitzungsspeicher
  persistiert. Das Token bleibt JavaScript-zugänglich wie im bestehenden
  Bearer-Vertrag, wird aber nicht browserübergreifend oder dauerhaft gespeichert.
- Privacy: Keine zusätzlichen Nutzer-, Projekt- oder Supportdaten werden
  persistiert oder protokolliert.
- Performance: Polling ist auf eine Anfrage pro zwei Sekunden und genau die aktive,
  sichtbare Runs-Ansicht begrenzt; keine überlappenden Anfragen.
- Reliability: Projekt-, Ansichts- und Sitzungswechsel müssen veraltete Antworten
  zuverlässig entwerten.
- Accessibility: Während der Sitzungsprüfung darf kein geschützter Inhalt kurzzeitig
  erscheinen; Status-/Fortschrittstexte bleiben für assistive Technologien lesbar.
- Compatibility: Bestehende Auth- und Analyse-Run-HTTP-Verträge sowie die
  serverseitige Sitzungsablaufzeit bleiben unverändert.
- Operability: Keine neue Abhängigkeit, kein neuer Dienst und keine neue
  Konfiguration.

## Constraints

- Die bestehende serverseitige Sitzungsdauer von zwölf Stunden bleibt als
  Sicherheitsgrenze bestehen. Browser-Tab-Schluss, explizite Abmeldung,
  serverseitiger Ablauf, Widerruf oder Benutzerlöschung beenden die nutzbare Sitzung.
- Ausschließlich lokale Entwicklungs-/Testressourcen ohne Produktionsdaten dürfen
  für Verifikation verwendet werden.
- Die vorhandenen Endpunkte `/api/auth/me`, `/api/auth/sign-out` und
  `/api/projects/{project_id}/analysis-runs` sind zu erweitern, nicht durch parallele
  Verträge zu ersetzen.

## In scope

- Sichere Wiederherstellung einer gültigen Frontend-Sitzung nach Reload.
- Explizite Frontend-Abmeldung gegen den vorhandenen Backend-Endpunkt.
- Gebundenes Polling der bestehenden Analyse-Run-Liste.
- Regressionstests und Aktualisierung der kanonischen MVP-Spezifikation.

## Out of scope / non-goals

- Unbegrenzte oder gleitend verlängerte serverseitige Sitzungen.
- Persistenz über geschlossene Tabs/Browsersitzungen hinweg.
- Refresh Tokens, Cookie-basierte Authentifizierung oder Änderung des Auth-Vertrags.
- WebSockets, Server-Sent Events oder ein neuer Run-Status-Endpunkt.
- Polling anderer Projektbereiche oder Hintergrundaktualisierung bei unsichtbarem
  Dokument.

## Acceptance criteria

- [x] AC-1: Nach erfolgreichem Login und Seiten-Reload wird bei gültigem Token ohne
  erneute Passworteingabe die geschützte Anwendung angezeigt.
- [x] AC-2: Ein gespeichertes ungültiges, abgelaufenes oder widerrufenes Token zeigt
  keine geschützten Inhalte und wird aus dem Sitzungsspeicher entfernt.
- [x] AC-3: Browser-Sitzungsspeicher enthält nur das Token, weder Passwort noch
  persistiertes Benutzerobjekt; ein neuer Browser-Tab ohne übernommenen
  Sitzungskontext startet abgemeldet.
- [x] AC-4: Explizites Abmelden ruft den vorhandenen Sign-out-Endpunkt auf und
  entfernt lokalen Auth-Zustand auch bei einem Netzwerkfehler.
- [x] AC-5: Beim Öffnen von Projekt → Runs erscheint sofort der aktuelle
  Serverzustand; Änderungen an Status, Fortschritt, Zeitstempeln, Diagnose oder
  Fehlermeldung erscheinen spätestens nach einem erfolgreichen Zwei-Sekunden-Poll
  ohne Seiten-Reload.
- [x] AC-6: Polling läuft nur für die aktive sichtbare Runs-Ansicht, überlappt nicht
  und endet bei Tab-/Projektwechsel, Logout oder Unmount.
- [x] AC-7: Verzögerte Antworten eines alten Projekts oder einer alten Sitzung
  verändern nicht die aktuelle Run-Liste.
- [x] AC-8: Vorübergehende Polling-Fehler behalten den letzten erfolgreichen Stand;
  spätere erfolgreiche Polls aktualisieren wieder normal.
- [x] AC-9: Die kanonische Spezifikation beschreibt Browser-Sitzungswiederherstellung
  und automatische Run-Aktualisierung als aktuellen Sollzustand.
- [x] AC-10: Fokussierte Frontendtests, relevante Qualitätsgates und
  `./.ai/tools/verify.sh` laufen erfolgreich; ein unabhängiger Security-fokussierter
  Review enthält keine offenen P0/P1-Findings.

## Available references

- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `backend/auth/service.py`
- `backend/api/app.py`
- `tests/api/test_auth_api_integration.py`
- `tests/api/test_analysis_run_api_integration.py`
- `docs/specifications/support-knowledge-miner-mvp1.md`

## Open questions

Keine. Der Decision Owner bestätigte die bestehende serverseitige
Zwölf-Stunden-Grenze, das Zwei-Sekunden-Intervall und die vorhandenen uncommitted
Änderungen als Implementierungs-Ausgangsbasis.

## Approval

- Owner: anfordernder Product Owner (Conversation User; Name nicht angegeben)
- Status: accepted
- Date: 2026-07-27
