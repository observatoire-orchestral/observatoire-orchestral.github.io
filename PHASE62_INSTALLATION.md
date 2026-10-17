# Phase 6.2 — Classement automatique conservateur

**Important :** Ce programme n'applique que les propositions à confiance « élevée » avec action « Proposition forte, à confirmer », sur des articles toujours `unreviewed` et sans `reviewed_by`. Il ne modifie ni `review_status`, ni `reviewed_by`, ni `reviewed_at`, ni les articles validés/rejetés. Les autres suggestions restent consultables dans l'interface Phase 6.1. Il ne supprime aucun article.

## Installation

1. Décompressez l'archive et téléversez son contenu dans le dépôt GitHub en conservant les dossiers.
2. GitHub > Actions > **Phase 6.2 - Appliquer les catégories proposées** > Run workflow > `preview`.
3. Vérifiez le nombre et les titres affichés dans le journal.
4. Relancez avec `apply` si le résultat vous convient.
5. Les membres peuvent ensuite revoir les articles dans le site et corriger la catégorie. L'application automatique **ne vaut pas validation humaine**.

**Aucune commande SQL n'est nécessaire.** La modification porte seulement sur `public.articles.category`, et seulement pour les articles dont les valeurs n'ont pas changé depuis l'audit. Le script est idempotent : une seconde exécution ne réapplique pas les mêmes changements.

Attention : la revue préliminaire n'a proposé que 18 changements de catégorie sur 2 882 articles, dont seulement 7 propositions fortes non protégées par une décision antérieure. Les autres catégories restent inchangées. Pour appliquer un plus grand volume, il faudrait refaire une classification plus approfondie, et non élargir aveuglément ces règles.
