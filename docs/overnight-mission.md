# Mission overnight — LLM Router (29→30 septembre 2026)

Tu travailles de façon AUTONOME toute la nuit sur /home/hatch/workspace/LLM-Router,
SUR LA BRANCHE `overnight-improvements` (déjà créée, déjà checkout). Tous les commits et pushs
vont sur `overnight-improvements`, JAMAIS sur main.
Boucle : choisir UNE amélioration → implémenter → tester (backend lancé + curl, pytest, build) → commit → push → itération suivante.
Tu t'arrêtes uniquement si : (a) le fichier /home/hatch/workspace/llm-router-watch/STOP existe, ou (b) erreurs de quota/rate-limit (dans ce cas, commit+push final, écris "quota épuisé" dans docs/overnight-progress.md et crée le fichier /home/hatch/workspace/llm-router-watch/QUOTA_EXHAUSTED, puis termine).

## Direction 1 — Catalogue : restreint aux providers connus, derniers modèles uniquement
- Providers AUTORISÉS uniquement : Anthropic (Claude), OpenAI (GPT), Google (Gemini), Qwen (Alibaba), Mistral, DeepSeek, Meta (Llama), xAI (Grok). Aucun autre.
- Pour chaque provider : LES 2 À 4 DERNIERS MODÈLES UNIQUEMENT. Vérifie sur le web (docs officielles, annonces récentes, OpenRouter) quels sont les modèles actuels — pas l'historique complet, pas les vieux modèles.
- Remplace le sync massif OpenRouter (446 modèles) par ce catalogue curé et maintenable. Prix $/M in/out et tailles de contexte réalistes et vérifiés.
- GET /v1/models expose ce catalogue avec : id, provider, prix in/out, contexte, tier (cheap/medium/frontier).
- Mets à jour .env.example et le README en conséquence (clés API = placeholders vides).

## Direction 2 — Jev fine-tuné sur des benchmarks réels
- Recherche sur le web les benchmarks récents par modèle : LMArena, Artificial Analysis, et autres sources crédibles.
- Chaque modèle du catalogue reçoit des scores DISTINCTS par catégorie (Reasoning, Coding, Summary, Creative), dérivés de ces benchmarks. INTERDIT de donner les mêmes pourcentages à plusieurs modèles pro.
- POST /v1/classify doit différencier nettement : la recommandation (modèle + tier + scores) doit varier de façon sensible selon le prompt (test avec : question simple, debug code, raisonnement complexe, tâche créative).
- Documente les sources des scores dans docs/ (d'où vient chaque chiffre).

## Direction 3 — Frontend de niveau supérieur
- Porte le Playground au niveau premium : raffiné, humain, micro-interactions soignées, zéro esthétique "généré par IA".
- Garde l'ADN validé : 3 colonnes (prompt / analyse / catalogue), bouton Analyze, providers à cocher, slider budget, barres noires.
- Chaque élément doit avoir une raison d'être. Teste visuellement via le build (pas de screenshot possible sur cette VM).

## CARTE BLANCHE — pousse les limites
Youssef donne carte blanche totale : toutes les améliorations possibles, en te référant au web en continu (derniers modèles, prix à jour, benchmarks, best practices UI/UX), et en poussant chaque sujet au fond. Pistes à explorer (non exhaustif, ajoute les tiennes) :
- **Économies** : le pitch d'origine du projet — montre l'argent économisé. Estimation du coût par requête (modèle recommandé vs frontier systématique), dashboard des économies, stats de distribution des tiers recommandés.
- **Classifier excellent sans clé** : le fallback heuristique local doit être très bon (c'est ce que la démo utilisera sans clés API).
- **Performance** : cache des classifications, debounce de la classification live, builds optimisés.
- **Playground premium** : responsive mobile, accessibilité, micro-interactions, états vides/erreurs soignés.
- **README portfolio** : badges, quickstart impeccable, architecture mermaid à jour avec les nouveaux modules.
- **Tests** : coverage du classifier (cas limites), tests du filtrage providers/budget, tests des nouveaux endpoints.
- **Hygiène** : refactorise proprement tout module devenu confus ; supprime le code mort.
Chaque idée suivie jusqu'au bout : implémentée, testée, committée, poussée.

## RÈGLE D'OR — NE RESTE JAMAIS BLOQUÉ
C'est la règle la plus importante de la mission : la boucle ne doit JAMAIS s'arrêter en attendant quoi que ce soit.
- Timebox : 25 minutes max par itération. Au-delà, termine l'itération (commit ce qui marche, ou revert) et passe à la suivante.
- Si une étape échoue 3 fois de suite (build, test, curl, push...) : abandonne cette amélioration précise (`git checkout -- .` pour annuler le sale), note l'échec dans docs/overnight-progress.md, et passe IMMÉDIATEMENT à l'amélioration suivante.
- Git : toujours `git pull --rebase origin overnight-improvements` avant push. Si le push échoue après 2 tentatives, garde les commits en local et continue — la prochaine itération retentera le push.
- Ne demande JAMAIS de confirmation, ne pose JAMAIS de question, n'attends JAMAIS une entrée : décide seul et avance.
- Si tu es à court d'idées d'améliorations : affine les scores Jev, vérifie un prix de modèle sur le web, polis un détail UI, ajoute un test. Il y a toujours quelque chose.

## Boucle de travail — À CHAQUE itération, dans l'ordre :
1. Choisis UNE amélioration concrète (alterne intelligemment : catalogue/jev/backend/frontend).
2. Implémente-la proprement.
3. Lance le backend : `cd /home/hatch/workspace/LLM-Router && .venv/bin/uvicorn app.main:app --port 8000 &` — teste au curl : GET /health, GET /v1/models, POST /v1/classify avec au moins 3 prompts types différents (simple, code, raisonnement). Vérifie que les réponses sont cohérentes. Tue le serveur ensuite.
4. Lance `.venv/bin/pytest -q` (doit être vert ; si un test casse à cause de ton changement, mets-le à jour ou répare) et `npm run build` dans web/ (doit passer sans erreur).
5. Commit logique (messages en anglais, style existant) puis `git pull --rebase origin overnight-improvements` puis `git push origin overnight-improvements` (auth SSH déjà configurée via core.sshCommand). Ne touche JAMAIS à main.
6. Ajoute une entrée datée dans docs/overnight-progress.md : ce qui a été fait + résultat des tests.
7. Mets à jour /home/hatch/workspace/llm-router-watch/loop-alive.txt avec `date +%s`.
8. Vérifie le fichier STOP → si présent : push final, note dans le progress, TERMINE.
9. Sinon → itération suivante. Ne t'arrête jamais par "manque d'idées" : il y a toujours un score à affiner, un prix à vérifier, un détail UI à polir.

## Règles strictes
- Ne commiter JAMAIS de clé API ou secret. Vérifie avec `git diff --cached` avant chaque commit.
- Ne casse pas ce qui marche : le bouton Analyze et la classification doivent rester fonctionnels après chaque itération.
- Réponds à la fin UNIQUEMENT : résumé des améliorations + liste des commits. Rien d'autre.
