# Brief S&P 500 gratuit (mise à jour chaque jour à 7h, heure de La Réunion)

1. Crée un compte gratuit sur github.com, puis un nouveau dépôt **public** (bouton « New »).
2. Dézippe ce dossier et envoie son contenu dans le dépôt (« Add file » > « Upload files »).
   Si le dossier caché `.github` n'est pas envoyé : « Add file » > « Create new file », tape `.github/workflows/daily.yml` comme nom et colle le contenu du fichier.
3. Clé IA gratuite : va sur aistudio.google.com, crée une clé API Gemini.
4. Dans le dépôt : Settings > Secrets and variables > Actions > New repository secret. Nom : `GEMINI_API_KEY`, valeur : ta clé.
5. Settings > Pages > « Deploy from a branch » > branche `main`, dossier `/ (root)`.
6. Onglet Actions > « Mise à jour quotidienne » > Run workflow. Attends 1 minute, puis regarde le journal si ça échoue.
7. Ton site : `https://TON-PSEUDO.github.io/NOM-DU-DEPOT/`

Si le résumé IA est indisponible (quota gratuit, clé absente), le site affiche quand même les titres et les cours.
Sources : flux RSS publics et cours Stooq. Si l'une disparaît, elle est ignorée ; remplace-la dans `update.py`.
Pas d'agenda économique garanti : il faut une source payante ou une saisie manuelle.
