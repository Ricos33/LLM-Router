# Mission overnight — LLM Router (29→30 septembre 2026)

## MISSION 29 SEPT APRÈS-MIDI — priorités de Youssef (lis en premier)
Nouveau cycle demandé par Youssef le 29/09 à 14h20. En plus de la boucle d'amélioration continue, ces 3 chantiers sont PRIORITAIRES :
1. **Fine-tuning du JSON envoyé à Jev** : le payload SystemOne doit être affiné pour de meilleurs résultats de routage. Améliore le schéma (champs, pondérations, fit scoring par modèle candidat), la sélection des candidats, et la calibration des scores. La clé Jev est encore vide (mock actif) : tout doit être excellent ET testé en mock, prêt pour la vraie clé.
2. **La partie "routing strategy" ne fonctionne pas bien** (constat de Youssef) : diagnostique pourquoi (les stratégies ne changent pas réellement le routage ? UI déconnectée du backend ?), répare, et prouve avec des tests + curl que chaque stratégie (balanced, cost_optimized, quality_optimized, etc.) produit un routage différent et cohérent.
3. **Améliorations de fonctionnalités** : implémente le BACKLOG VERROUILLÉ ci-dessous (validé par Youssef), dans l'ordre, en gardant le repo propre et présentable pour GitHub/LinkedIn.

Tu travailles de façon AUTONOME toute la nuit sur /home/hatch/workspace/LLM-Router,
SUR LA BRANCHE `overnight-improvements` (déjà créée, déjà checkout). Tous les commits et pushs
vont sur `overnight-improvements`, JAMAIS sur main.
Boucle : choisir UNE amélioration → implémenter → tester (backend lancé + curl, pytest, build) → commit → push → itération suivante.
Tu t'arrêtes uniquement si : (a) le fichier /home/hatch/workspace/llm-router-watch/STOP existe, ou (b) erreurs de quota/rate-limit (dans ce cas, commit+push final, écris "quota épuisé" dans docs/overnight-progress.md et crée le fichier /home/hatch/workspace/llm-router-watch/QUOTA_EXHAUSTED, puis termine).

## CHANTIER FRONTEND — amélioration gigantesque (demandé par Youssef le 29/09 à 14h30)
Le frontend doit passer au niveau "produit commercial". Travaille-le en parallèle du backlog backend : alterne les itérations (environ 1 itération frontend pour 2 backend).
1. **Design system** : typographie soignée (pas de police système générique), palette restreinte et cohérente, dark mode premium + light mode propre, espacement rigoureux. Zéro esthétique "généré par IA".
2. **Playground** : micro-interactions (transitions, skeletons pendant le chargement), streaming des réponses, boutons 👍/👎 de feedback, coût estimé AVANT envoi bien visible.
3. **Nouvelles vues** : Analytics enrichie (graphiques coût/latence par modèle, taux de hit du cache, économies cumulées), page de gestion des clés API virtuelles, historique des requêtes consultable.
4. **UI des features du backlog** : chaque feature backend (guardrails, A/B testing, feedback, cache sémantique) doit avoir son interface dédiée.
5. **Responsive mobile + accessibilité** : utilisable au téléphone, navigation clavier, contrastes suffisants, états vides et erreurs soignés.
Garde l'ADN validé par Youssef : 3 colonnes (prompt / analyse / catalogue), providers à cocher, slider budget, barres noires, classification live pendant la frappe.

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

## BACKLOG VERROUILLÉ — imposé par Lmoudir, validé par Youssef le 29/09 à 14h30
La carte blanche est TERMINÉE. Tu n'inventes plus de fonctionnalités : tu implémentes CE backlog, DANS L'ORDRE, un item à la fois. Chaque item = une itération (découpe en sous-itérations si trop gros, chacune testée et committée).
Contexte marché (recherche Lmoudir 29/09) : les gateways de référence sont LiteLLM (virtual keys, budgets, fallbacks), Portkey (cache sémantique, 50+ guardrails), Cloudflare AI Gateway (cache, rate limiting), OpenRouter (fallbacks). Ce backlog aligne le routeur sur ces standards.

### Ordre d'exécution (ne pas changer l'ordre)
1. **Fallback réel sur échec** — `get_fallback_candidates()` existe dans app/router/engine.py : vérifie qu'il est branché sur l'EXÉCUTION réelle. Si le backend primaire timeout ou renvoie une erreur, retry transparent sur le candidat suivant avec backoff exponentiel + jitter. Preuve : test qui simule un backend en échec et vérifie que la réponse vient du fallback.
2. **Timeouts configurables par tier** — chaque tier (cheap/medium/frontier) a son timeout propre, configurable via settings/env. Le timeout déclenche le fallback (item 1).
3. **Cache sémantique** — le ResponseCache actuel ne fait que l'exact-match. Ajoute la détection de prompts quasi-identiques (normalisation agressive + similarité textuelle robuste ; embeddings seulement si une clé est disponible). Le dashboard montre le taux de hit et les $ économisés.
4. **Clés API virtuelles** — émettre des clés par application/équipe (ex: `sk-router-...`), chacune avec son budget et son rate limit propres. Les vraies clés providers restent cachées côté serveur. Endpoints : créer/lister/révoquer. Standard LiteLLM/Portkey.
5. **Guardrails PII** — avant d'envoyer un prompt au provider : détection et masquage des données personnelles (emails, téléphones, IBAN, noms propres configurables). Opt-in par clé virtuelle ou global. Logger CE QUI a été masqué (type de donnée), jamais la valeur.
6. **Feedback loop** — endpoint pour noter une réponse (👍/👎) ; le feedback ajuste les fit scores du classifier au fil du temps (poids croissant avec le nombre de votes, anti-abus basique). UI : boutons dans le Playground.
7. **A/B testing** — router un % configurable du trafic vers un modèle "challenger" et comparer coût/latence/feedback dans le dashboard.

### Definition of Done (chaque item, sans exception)
- `pytest -q` vert, avec nouveaux tests couvrant le comportement (cas limites inclus).
- Preuve `curl` contre le backend lancé : l'item se comporte comme décrit.
- Entrée datée dans docs/overnight-progress.md.
- Commit (anglais, style existant) + push sur overnight-improvements. JAMAIS main.

### Quand le backlog est épuisé
Reviens sur : affinage des scores Jev / calibration, vérification de prix sur le web, polish UI, ajout de tests. Ne réinvente pas de features hors backlog.

## RÈGLE D'OR — NE RESTE JAMAIS BLOQUÉ
C'est la règle la plus importante de la mission : la boucle ne doit JAMAIS s'arrêter en attendant quoi que ce soit.
- Timebox : 25 minutes max par itération. Au-delà, termine l'itération (commit ce qui marche, ou revert) et passe à la suivante.
- Si une étape échoue 3 fois de suite (build, test, curl, push...) : abandonne cette amélioration précise (`git checkout -- .` pour annuler le sale), note l'échec dans docs/overnight-progress.md, et passe IMMÉDIATEMENT à l'amélioration suivante.
- Git : toujours `git pull --rebase origin overnight-improvements` avant push. Si le push échoue après 2 tentatives, garde les commits en local et continue — la prochaine itération retentera le push.
- Ne demande JAMAIS de confirmation, ne pose JAMAIS de question, n'attends JAMAIS une entrée : décide seul et avance.
- Si tu es à court d'idées d'améliorations : prends le prochain item du BACKLOG VERROUILLÉ. Si le backlog est épuisé : affine les scores Jev, vérifie un prix de modèle sur le web, polis un détail UI, ajoute un test. Il y a toujours quelque chose.

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

## ROTATION DES MODÈLES — le travail ne s'arrête jamais
Ordre de rotation (ne jamais changer l'ordre) :
1. `gemini-3.1-pro-high`
2. `claude-opus-4-6-thinking`
3. `claude-sonnet-4-6`
4. `gpt-oss-120b-medium`
5. `gemini-3.8-flash-high`

- Au démarrage, lis `~/workspace/llm-router-watch/` : si un fichier `QUOTA_<model>` existe pour le modèle que tu utilises, ne démarre pas et termine proprement.
- Quand TON modèle est en quota épuisé (erreurs quota / rate-limit répétées pendant plusieurs minutes, pas une erreur isolée) :
  1. Commit + push tout ce qui est en cours (`git pull --rebase origin overnight-improvements` puis push).
  2. Note l'épuisement dans `docs/overnight-progress.md`.
  3. Crée `~/workspace/llm-router-watch/QUOTA_<model-id-exact>` (ex : `QUOTA_gemini-3.1-pro-high`).
  4. Termine ton tour PROPREMENT (exit 0). Un superviseur relancera automatiquement la boucle sur le modèle suivant de la liste.
- Ne crée JAMAIS toi-même `QUOTA_EXHAUSTED` : c'est le superviseur qui le crée quand tous les modèles sont épuisés.

## ANTI-ARRÊT — lis ceci en premier
Tu travailles en boucle INFINIE à l'intérieur d'un SEUL tour : ne termine JAMAIS ton tour pour poser une question ou faire un résumé intermédiaire. Décide seul des priorités (le BACKLOG VERROUILLÉ donne l'ordre exact) et enchaîne les itérations sans interruption. Tu ne t'arrêtes que si : le fichier STOP existe, ou TON modèle est en quota épuisé (auquel cas suis le protocole ROTATION DES MODÈLES : push, journal, `QUOTA_<model>`, exit propre).
