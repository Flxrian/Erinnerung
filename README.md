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

**Login (als HTML-Datei bzw. auf eigener Webseite):** Beim ersten Öffnen ein Konto mit Benutzername und Passwort erstellen. Jedes Konto sieht nur seine eigenen Wochen; die Daten werden mit dem Passwort verschlüsselt (AES-GCM, Schlüssel per PBKDF2) im Browser gespeichert. Konten gelten nur für das Gerät/den Browser, auf dem sie erstellt wurden.

**Admin:** Es gibt genau einen fest eingebauten Admin (Login-Reiter „Admin“, nur mit dem Admin-Passwort). Niemand kann sich selbst zum Admin machen. Der Admin sieht alle Benutzer, kann vergessene Passwörter neu setzen (die Wochen bleiben erhalten), Konten löschen und das Admin-Passwort ändern. Technisch: Jeder Benutzer hat einen zufälligen Datenschlüssel, der zusätzlich mit dem öffentlichen RSA-Schlüssel des Admins gesichert ist. Ältere Konten werden beim nächsten Login des Benutzers zurücksetzbar. Ein geändertes Admin-Passwort gilt im jeweiligen Browser; das ursprüngliche Admin-Passwort funktioniert immer. Benutzer können ihr Passwort unter „Meine Daten“ selbst ändern.

Alle Daten bleiben lokal im Browser. Über **Backup exportieren/importieren** lassen sie sich sichern oder auf ein anderes Gerät übertragen. Aus dem Log kann jede Woche erneut geöffnet, bearbeitet oder als PDF geladen werden.

## Abo und Zugangskeys (HTML-Version)

- Zugang nur mit Abo (5 € pro Monat) oder Zugangskey vom Admin. Neue Konten sehen nach der Registrierung sofort die Bezahlseite (einstellbarer Testzeitraum `trialDays`, Standard 0).
- Der Admin erstellt Zugangskeys im Admin-Bereich unter „Zugangskeys“: Benutzername + Laufzeit (1, 3, 6, 12 Monate oder unbegrenzt). Keys sind mit dem Admin-Schlüssel signiert (ECDSA P-256), gelten nur für den angegebenen Benutzernamen und können nicht gefälscht werden.
- Einlösen: auf der Sperrseite oder später unter „Meine Daten → Zugangskey eingeben“.
- Bezahlt wird per PayPal an florian@kurth-dn.com: als monatliches Abo oder einmalig für einen Monat. Der Benutzername steht automatisch im Verwendungszweck. Einstellungen oben im Skript im Objekt `ABO` (`paypal`, `amount`, `price`, `trialDays`, optional `paymentUrl`).
- Grenzen: Ohne Server prüft nur der Browser. Wer die HTML-Datei bearbeitet oder die Systemuhr zurückstellt, kann die Sperre umgehen. Zahlungen werden nicht automatisch erkannt: nach Zahlungseingang erstellt der Admin den Key von Hand.
