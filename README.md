# Observatoire des orchestres — SUDCT 44 (V3)

Application PWA installable, collecte RSS programmée, authentification Supabase et validation facultative.

## 1. Créer le projet Supabase
1. Ouvrir https://supabase.com et créer un projet sur l'offre gratuite (quotas et conditions susceptibles de changer).
2. Dans **SQL Editor**, coller et exécuter `supabase/schema.sql`.
3. Dans **Authentication > Providers > Email**, activer l'authentification e-mail ; activer la confirmation e-mail de préférence.
4. Dans **Authentication > URL Configuration**, définir l'URL du site GitHub Pages et les URL de redirection autorisées.
5. Dans **Project Settings > API** (ou section API Keys), copier **Project URL** et la clé **publishable/anon** dans `config.js`.
6. NE JAMAIS placer la clé **service_role / secret** dans `config.js` ou dans le dépôt.

## 2. Publier sur GitHub Pages
1. Créer un dépôt GitHub, par exemple `observatoire-sudct44` (un dépôt public est le plus simple pour GitHub Pages gratuit).
2. Envoyer **tout le contenu** de ce dossier à la racine du dépôt, y compris `.github/workflows/veille.yml`.
3. Dans **Settings > Pages**, choisir **Deploy from a branch**, branche `main`, dossier `/ (root)`.
4. Attendre la publication à `https://VOTRE_COMPTE.github.io/observatoire-sudct44/`.
5. Ouvrir l'adresse, créer un compte, confirmer l'e-mail et se connecter.
6. Dans Supabase **Authentication > Users**, copier l'UUID du compte principal et exécuter dans SQL Editor :
   `update public.profiles set role='admin' where id='UUID_DU_COMPTE';`
   Pour accorder les droits de validation à un autre compte, utiliser `role='reviewer'`.

**Sécurité :** avec l'inscription publique activée, toute personne peut demander un compte et lire les articles après inscription. Pour un groupe fermé, désactiver les nouvelles inscriptions dans Supabase après création des comptes, ou utiliser des invitations administrateur. Ne pas saisir de documents syndicaux confidentiels dans cette V1.

## 3. Activer la collecte automatique
1. Dans GitHub > **Settings > Secrets and variables > Actions**, créer deux **Repository secrets** :
   - `SUPABASE_URL` : URL du projet Supabase
   - `SUPABASE_SERVICE_ROLE_KEY` : clé secrète `service_role` (jamais dans un fichier public)
2. Dans **Actions > Collecte des actualités > Run workflow**, lancer la première collecte manuellement.
3. Contrôler les journaux et l'arrivée des articles dans l'application.
4. Le workflow tourne normalement trois fois par jour (horaires UTC, pouvant être retardés par GitHub). Sur un dépôt public, les actions programmées peuvent être désactivées après une période d'inactivité.

## 4. Installer l'application
- **iPhone** : ouvrir l'URL dans Safari > Partager > Sur l'écran d'accueil.
- **Android** : ouvrir l'URL dans Chrome > Installer l'application ou Ajouter à l'écran d'accueil.
- Le site doit être servi en HTTPS (GitHub Pages le fait). Les données ne sont pas disponibles hors connexion ; seul le shell peut être mis en cache.

## 5. Fonctionnement et limites
- Publication immédiate des articles collectés avec statut **Non examiné** ; les reviewers peuvent **Valider**, **Rejeter** ou **Remettre en attente**.
- Les articles rejetés restent visibles aux membres, avec leur statut. Le filtrage est possible.
- Flux Google Actualités RSS (requêtes par orchestre et mots-clés). **Aucune IA générative n'est utilisée** : le classement est fondé sur des mots-clés. L'exhaustivité, la qualité et la disponibilité des résultats ne sont pas garanties.
- Les liens peuvent mener à Google Actualités avant redirection vers l'éditeur. Les résumés RSS ne sont pas des vérifications indépendantes.
- Les doublons d'URL sont ignorés, mais un même article peut avoir plusieurs URL ; une amélioration ultérieure peut normaliser les liens.
- La liste est limitée aux 500 articles les plus récents dans l'interface ; l'export porte sur ces 500 lignes.
- Les clés Supabase publiques sont protégées par les politiques RLS ; les secrets de collecte restent dans GitHub Actions.
- L'icône SVG est supportée par de nombreux navigateurs ; pour une meilleure compatibilité iOS, ajouter ultérieurement une icône PNG 192/512 et apple-touch-icon.
- Vérifier régulièrement les quotas et les conditions d'utilisation de GitHub, Supabase et Google Actualités.

## 6. Développement local
`python3 -m http.server 8080` puis ouvrir `http://localhost:8080` (ajouter cette URL aux redirections Supabase si nécessaire).

## 7. Avant une mise en service syndicale réelle
- Restreindre les inscriptions, vérifier la politique de confidentialité/RGPD et désigner les responsables des comptes.
- Ne pas traiter les informations privées des adhérents sans analyse de conformité.
- Envisager des sauvegardes de la base, une journalisation des validations et une authentification renforcée.
