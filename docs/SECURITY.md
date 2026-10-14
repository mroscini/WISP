# Sicurezza e privacy

WISP elabora dati localmente, ma “locale” non significa automaticamente “sicuro”.

- Il pannello non ha autenticazione, per scelta esplicita di questa versione. Usalo solo su una LAN fidata.
- Non configurare port forwarding e non esporre la porta 8787 a Internet.
- Gli upload accettano soltanto `.txt` e `.md` UTF-8 e hanno un limite configurabile, massimo 10 MiB.
- I documenti sono identificati con UUID; i percorsi vengono risolti e verificati prima dell’accesso.
- Il browser riceve CSP, `X-Frame-Options`, `nosniff` e una policy referrer restrittiva.
- Le configurazioni e gli indici vengono sostituiti atomicamente per ridurre il rischio di corruzione.
- Non caricare dati personali non necessari o materiali di cui non possiedi i diritti.

Il RAG limita alcune invenzioni ma non garantisce risposte appropriate ai bambini. La supervisione adulta rimane necessaria.

