# Tätigkeitsbericht – Meine Ausbildung

Online-Version: https://claude.ai/artifact/FtzQjZG3iMa8vt9CFHSJJi

Online meldet sich jede Person mit ihrem eigenen claude.ai-Konto an. Texte, Einstellungen und gespeicherte Wochen liegen privat in diesem Konto, niemand sonst (auch nicht die Erstellerin bzw. der Ersteller) sieht sie. Damit andere die Seite nutzen und speichern können, über das Teilen-Menü der Seite einladen: im Team-/Enterprise-Plan mindestens als „Contributor“, sonst per E-Mail als „Editor“.

Webseite zum schnellen Ausfüllen des wöchentlichen Tätigkeitsberichts (Mo–Sa) als PDF.

## Benutzung

1. `index.html` im Browser öffnen (Doppelklick genügt, Internet wird nur für die PDF-Bibliothek gebraucht).
2. Rechts **Name/Vorname** und unter **Meine Texte** eigene Tätigkeiten eintragen – ein Text pro Zeile, Stunden optional nach `|`, z. B. `Kunden beraten | 1,5`.
3. Optional unter **Feste Texte je Wochentag** feste Einträge hinterlegen (z. B. Mittwoch: Berufsschule). Steht dort nur `arbeitsfrei`, wird der Tag als frei markiert (Samstag ist so voreingestellt).
4. Oben **Jahr und KW** im Dropdown wählen oder ein Datum im Kalender anklicken.
5. **Automatisch ausfüllen** füllt jede leere Zeile. Die **Vorschau** zeigt live das eingescannte Originalformular mit deinen Einträgen. Sobald alle Zeilen voll sind, wird das fertige PDF (Originalformular als Hintergrund) erstellt, die Woche im **Log** gespeichert und das Formular für die nächste KW geleert.

**Login (als HTML-Datei bzw. auf eigener Webseite):** Beim ersten Öffnen ein Konto mit Benutzername und Passwort erstellen. Jedes Konto sieht nur seine eigenen Wochen; die Daten werden mit dem Passwort verschlüsselt (AES-GCM, Schlüssel per PBKDF2) im Browser gespeichert. Konten gelten nur für das Gerät/den Browser, auf dem sie erstellt wurden. Passwort vergessen = Daten nicht mehr lesbar.

Alle Daten bleiben lokal im Browser. Über **Backup exportieren/importieren** lassen sie sich sichern oder auf ein anderes Gerät übertragen. Aus dem Log kann jede Woche erneut geöffnet, bearbeitet oder als PDF geladen werden.
