# Real-Time Streaming Events - Orchestration

## 1. Überblick & Features
Dieser Prototyp demonstriert eine Online-Streaming-Lösung zur Echtzeit-Prozessüberwachung im hellen Design (**Light Mode**):

- **Mehrere Prozesse mit bis zu ~50 Cases:**
  1. `PROC-001` — *Order-to-Cash & Credit Approval Process* (bis zu 48 Cases)
  2. `PROC-002` — *Purchase-to-Pay & Invoice Approval* (bis zu 28 Cases)
  3. `PROC-003` — *Customer Onboarding & KYC Compliance* (bis zu 16 Cases)
- **Aggregierte Event-Zahlen im Petri-Netz:** Wird in der *Process Overview* das Petri-Netz eines Prozesses ohne ausgewählten Case betrachtet, steht in jedem Event-/Transitionskasten die Anzahl der Cases, die dieses Event bis zum gewählten Zeitpunkt durchlaufen haben.
- **Zeit-Simulation (Stream Time Snapshots):** Über die Zeitleiste im Header (`09:00`, `11:00`, `13:30`, `16:00 (Latest)`) lässt sich der Zustand zu verschiedenen Zeitpunkten anzeigen, um zu verfolgen, wie neue Cases eintreffen und bestehende Cases im Petri-Netz voranschreiten.
- **Last Update (Neu hinzugekommene Cases):** Im Hauptmenü zeigt die Kachel **🆕 Last Update** alle im aktuellen Zeitfenster neu hinzugekommenen Cases. Zudem wird bei jedem Case im gesamten Tool per Badge angezeigt, ob er aus dem letzten Update stammt (`🆕 From Last Update`).
- **Zwei auswählbare Detection Methods:**
  1. **Petri-Net Conformance Checking:** Erkennt übersprungene Pflichtschritte (*Severe Deviations*), Rework-Schleifen und wiederholte Schritte (*Minor Deviations*).
  2. **SLA & Timestamp Monitoring:** Visualisiert Schritt- und Fall-Deadlines mittels Fortschrittsbalken und hebt Fristüberschreitungen farblich hervor.
- **Klick außerhalb schließt aktive Ansicht:** Ein Klick außerhalb der angezeigten Panels führt jederzeit direkt zurück zum Hauptmenü.

---

## 2. Starten des Prototyps

Doppelklicke auf **`start_prototype.bat`** oder führe im Terminal aus:
```powershell
& "C:\Users\johan\AppData\Local\Python\pythoncore-3.15-64\python.exe" app.py
```
Öffne anschließend im Browser: **`http://127.0.0.1:8000`**
