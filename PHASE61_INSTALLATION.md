# Phase 6.1 — Installation sûre

Cette mise à jour **n’applique pas automatiquement de corrections aux articles**. Elle importe 2 882 propositions historiques dans une table séparée, visible dans le site. Les membres habilités peuvent ensuite corriger les catégories une par une.

1. Faites une sauvegarde de votre dépôt GitHub actuel. Décompressez ce ZIP. Dans le dépôt `observatoire-orchestral.github.io`, importez les fichiers du dossier `observatoire-orchestral.github.io-main` **en conservant l’arborescence**. Ne supprimez pas vos autres fichiers. Ne remplacez pas votre `config.js` s’il contient déjà vos paramètres valides.
2. Dans Supabase → SQL Editor, exécutez **uniquement** `supabase/PHASE61_EDITORIAL_SUGGESTIONS.sql`. Ne lancez pas `schema.sql`.
3. GitHub → Actions → `Phase 6.1 - Import des propositions éditoriales` → Run workflow → `preview`. Le log doit indiquer combien de lignes correspondent encore aux articles existants.
4. Relancez avec `apply`. Cela écrit **uniquement** dans `public.editorial_suggestions`. Aucune ligne de `public.articles` ou `public.profiles` n’est modifiée.
5. Ouvrez le site et rechargez la page. Le filtre « Priorité de relecture » et les recommandations doivent apparaître. Les membres avec rôle `reviewer` ou `admin` peuvent appliquer une catégorie proposée **article par article**. Le statut `validated`, `rejected` ou `unreviewed` est conservé.

## Garanties
- Import idempotent par `article_id`; 2 882 identifiants uniques vérifiés.
- En cas de titre/catégorie/orchestre modifiés depuis l’audit, la suggestion est ignorée à l’import.
- Pas de suppression ni de modification automatique des articles ou comptes.
- Les suggestions proviennent de titres/résumés; elles ne constituent pas une lecture intégrale des articles. Vérifiez les propositions avant de les accepter.
- La table des suggestions n’est lisible que par les comptes approuvés et n’est modifiable que via le rôle serveur GitHub.
- Pour les articles nouvellement collectés, il n’existe pas encore de proposition : le filtre « Sans pré-analyse » permet de les identifier.
