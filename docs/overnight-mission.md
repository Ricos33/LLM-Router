# Mission overnight — LLM Router (29→30 septembre 2026)

## MISSION 29 SEPT APRÈS-MIDI — priorités de Youssef (lis en premier)
Nouveau cycle demandé par Youssef le 29/09 à 14h20. En plus de la boucle d'amélioration continue, ces 3 chantiers sont PRIORITAIRES :
1. **Fine-tuning du JSON envoyé à Jev** : le payload SystemOne doit être affiné pour de meilleurs résultats de routage. Améliore le schéma (champs, pondérations, fit scoring par modèle candidat), la sélection des candidats, et la calibration des scores. La clé Jev est encore vide (mock actif) : tout doit être excellent ET testé en mock, prêt pour la vraie clé.
2. **La partie "routing strategy" ne fonctionne pas bien** (constat de Youssef) : diagnostique pourquoi (les stratégies ne changent pas réellement le routage ? UI déconnectée du backend ?), répare, et prouve avec des tests + curl que chaque stratégie (balanced, cost_optimized, quality_optimized, etc.) produit un routage différent et cohérent.
3. **Améliorations de fonctionnalités** : continue d'ajouter des features utiles (voir section FONCTIONNALITÉS), en gardant le repo propre et présentable pour GitHub/LinkedIn.

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

## FONCTIONNALITÉS — ton jugement, recherche web profonde
Au-delà de la liste ci-dessus : ajoute TOUTE fonctionnalité que tu juges bonne pour le projet. Passe du temps sur le web : étudie les routeurs et gateways existants (OpenRouter, Jev Router, LiteLLM, Portkey, OpenAI, Vercel AI Gateway...), repère ce qui fait leur force, et implémente ce qui rendrait ce routeur objectivement meilleur et plus impressionnant en portfolio. Exemples pour démarrer (dépasse-les) :
- Fallback automatique : si le modèle recommandé échoue ou timeout, retry transparent sur le suivant.
- Comparaison côte-à-côte : même prompt envoyé à 2-3 modèles, résultats et coûts comparés.
- Mode benchmark : batterie de prompts types, tableau coût/qualité/vitesse estimés par modèle.
- Historique des requêtes + analytics enrichies (persistance locale).
- Export des résultats (JSON/CSV).
- Clés API par provider configurables depuis l'UI (stockage local).
- Rate limiting / budget mensuel avec alertes.
Ne te limite pas : si une fonctionnalité sert la vision (routeur intelligent, économique, présentable), construis-la.

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
Tu travailles en boucle INFINIE à l'intérieur d'un SEUL tour : ne termine JAMAIS ton tour pour poser une question ou faire un résumé intermédiaire. Décide seul des priorités (la section FONCTIONNALITÉS donne des pistes) et enchaîne les itérations sans interruption. Tu ne t'arrêtes que si : le fichier STOP existe, ou TON modèle est en quota épuisé (auquel cas suis le protocole ROTATION DES MODÈLES : push, journal, `QUOTA_<model>`, exit propre).
