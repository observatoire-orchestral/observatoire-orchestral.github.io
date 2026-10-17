# Phase 6.3 — Appliquer toutes les propositions de catégories

Ce paquet supprime le seuil de confiance et traite **toutes** les différences entre `category_current` et `category_preliminary` du fichier de 2 882 articles. Ce fichier ne contient que **18 changements de catégorie** : les 2 864 autres propositions conservent la catégorie actuelle. Ce paquet ne constitue donc **pas** une nouvelle analyse éditoriale complète.

Le programme protège les articles dont `reviewed_by` est renseigné et vérifie l’ancienne catégorie, l’orchestre et le titre avant chaque écriture. Il ne modifie ni statut de validation ni auteur de validation, et ne supprime aucun article. Un article marqué « validated » sans identifiant de réviseur peut être reclassé, mais son statut reste « validated » : cette ambiguïté préexistante est conservée.

1. Décompressez et téléversez les fichiers dans le dépôt GitHub, sans supprimer les fichiers existants.
2. GitHub → Actions → **Phase 6.3 - Appliquer toutes les propositions de catégories** → Run workflow → `preview`.
3. Examinez le journal, puis relancez avec `apply`.
4. Les membres peuvent ensuite corriger les catégories depuis l’interface.

Aucun SQL nouveau nécessaire. Une seconde exécution ne réapplique pas les modifications déjà faites.
