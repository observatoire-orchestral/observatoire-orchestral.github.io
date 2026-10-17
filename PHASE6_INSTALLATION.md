# Phase 6 — Relecture éditoriale intégrale

## Installation
1. Sur GitHub, ouvrez le dépôt `observatoire-orchestral/observatoire-orchestral.github.io`. Uploadez les fichiers de ce ZIP **en conservant leurs dossiers** (ou remplacez les fichiers modifiés). Ne supprimez pas `config.js` ni les secrets GitHub.
2. Dans Supabase > SQL Editor, exécutez **uniquement** `supabase/PHASE6_EDITORIAL_PERMISSIONS.sql` pour permettre aux membres habilités de corriger catégories et orchestres. **N'exécutez pas `schema.sql`.**
3. GitHub > Actions > **Phase 6 - Audit intégral (lecture seule)** > Run workflow. Téléchargez l'artifact `phase6-audit-complet` : il contient `all_articles.csv` (une ligne par article) et `summary.txt`. **Aucune écriture Supabase** lors de cet audit.
4. Rechargez le site (au besoin avec actualisation forcée). Les profils `reviewer` et `admin` peuvent valider, écarter, remettre à vérifier ou corriger le classement. Les autres membres consultent les articles.

## Fonctionnement et limites
- Tous les articles, y compris ceux jugés incertains, restent visibles dans la base et filtrables par état.
- Les décisions humaines existantes ne sont pas écrasées par l'audit ; les 45 corrections historiques sont préservées.
- `all_articles.csv` contient des propositions **automatiques**, pas des décisions approuvées ; ne l'importez pas dans Supabase.
- Les catégories proposées utilisent les règles actuelles, dont certaines peuvent encore se tromper ; aucune modification automatique des 2 882 enregistrements n'est effectuée.
- Le statut `rejected` signifie « écarté » par un membre, et n'efface jamais l'article.
- Pour donner le rôle `reviewer` à un membre, l'administrateur doit mettre à jour son profil via Supabase en respectant les procédures existantes.
- Le nombre d'articles peut dépasser 2 882 depuis la dernière collecte.
- Les corrections manuelles marquent l'article `validated` et enregistrent l'identité du membre.
- La gestion des validations est soumise aux politiques RLS existantes : si une opération échoue, vérifiez le rôle du membre et les politiques RLS.
