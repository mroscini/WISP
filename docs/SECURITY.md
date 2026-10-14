# Sicurezza e privacy

WISP elabora dati localmente, ma “locale” non significa automaticamente “sicuro”.

- Il pannello non ha autenticazione, per scelta esplicita di questa versione. Usalo solo su una LAN fidata.
- Non configurare port forwarding e non esporre la porta 8787 a Internet.
- Gli upload accettano soltanto `.txt` e `.md` UTF-8 e hanno un limite configurabile, massimo 10 MiB.
- I documenti sono identificati con UUID; i percorsi vengono risolti e verificati prima dell’accesso.
- Il browser riceve CSP, `X-Frame-Options`, `nosniff` e una policy referrer restrittiva.
- Le configurazioni e gli indici vengono sostituiti atomicamente per ridurre il rischio di corruzione.
- Non caricare dati personali non necessari o materiali di cui non possiedi i diritti.
- La API key ElevenLabs viene salvata in `data/.secrets.json` con permessi locali restrittivi e non viene restituita dalle API del pannello.
- Poiché il pannello non usa autenticazione né HTTPS, inserisci una API key soltanto su una LAN privata e fidata. Preferisci una chiave ElevenLabs con permessi limitati e un tetto di spesa.
- ElevenLabs è un servizio cloud: quando è selezionato, il testo delle risposte lascia il dispositivo per essere sintetizzato.

Il RAG limita alcune invenzioni ma non garantisce risposte appropriate ai bambini. La supervisione adulta rimane necessaria.

