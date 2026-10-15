
/* Observatoire SUD ONPL */
(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const show = (id, yes) => $(id).classList.toggle('hidden', !yes);

  const notice = (msg, error = false) => {
    $('notice').textContent = msg;
    $('notice').className = msg
      ? 'notice' + (error ? ' error' : '')
      : '';
  };

  const conf = window.SUDCT_CONFIG || window.SUD_CONFIG || {};

  if (
    !conf.supabaseUrl?.startsWith('https://') ||
    !conf.supabaseAnonKey ||
    /^(PASTE_|REMPLACER|YOUR_)/i.test(conf.supabaseAnonKey) ||
    !window.supabase
  ) {
    show('setup', true);
    return;
  }

  const db = window.supabase.createClient(
    conf.supabaseUrl,
    conf.supabaseAnonKey,
    {
      auth: {
        flowType: 'pkce',
        detectSessionInUrl: true
      }
    }
  );

  let currentUser = null;
  let isAdmin = false;
  let records = [];
  let shown = 0;

  const pageSize = 40;

  const statusText = {
    unreviewed: 'Non examiné',
    validated: 'Validé',
    rejected: 'Rejeté'
  };

  const esc = s => String(s ?? '').replace(
    /[&<>"']/g,
    c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c])
  );

  function validUrl(s) {
    try {
      const u = new URL(s);
      return ['http:', 'https:'].includes(u.protocol)
        ? u.href
        : '#';
    } catch {
      return '#';
    }
  }

  function account() {
    $('account').replaceChildren();

    if (!currentUser) return;

    const b = document.createElement('button');
    b.className = 'secondary';
    b.textContent = 'Déconnexion';
    b.onclick = () => db.auth.signOut();

    $('account').append(b);
  }

  async function boot() {
    notice('');

    const { data: { user }, error } = await db.auth.getUser();

    if (error && error.name !== 'AuthSessionMissingError') {
      console.warn(error);
    }

    currentUser = user;
    account();

    show('auth', !user);
    show('pending', false);
    show('dashboard', false);

    if (!user) return;

    const { data: profile, error: pe } = await db
      .from('profiles')
      .select('approved,role')
      .eq('id', user.id)
      .single();

    if (pe) {
      notice(
        'Impossible de vérifier votre compte : ' + pe.message,
        true
      );
      show('pending', true);
      return;
    }

    if (!profile?.approved) {
      show('pending', true);
      return;
    }

    isAdmin = profile.role === 'admin';

    show('dashboard', true);
    await load();
  }

  $('loginForm').addEventListener('submit', async e => {
    e.preventDefault();

    const { error } = await db.auth.signInWithPassword({
      email: $('email').value.trim(),
      password: $('password').value
    });

    if (error) {
      notice(error.message, true);
    } else {
      await boot();
    }
  });

  $('signup').onclick = async () => {
    const email = $('email').value.trim();
    const password = $('password').value;

    if (!email || !password) {
      notice('Saisissez votre e-mail et votre mot de passe.', true);
      return;
    }

    const { error } = await db.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: location.origin + location.pathname
      }
    });

    notice(
      error
        ? error.message
        : 'Inscription envoyée. Confirmez votre e-mail, puis attendez la validation de votre compte.',
      !!error
    );
  };

  $('reset').onclick = async () => {
    const email = $('email').value.trim();

    if (!email) {
      notice('Saisissez votre adresse e-mail.', true);
      return;
    }

    const { error } = await db.auth.resetPasswordForEmail(
      email,
      {
        redirectTo: location.origin + location.pathname
      }
    );

    notice(
      error
        ? error.message
        : 'Si ce compte existe, un e-mail de réinitialisation a été envoyé.',
      !!error
    );
  };

  db.auth.onAuthStateChange(event => {
    if (event === 'PASSWORD_RECOVERY') {
      setTimeout(async () => {
        const pw = prompt(
          'Nouveau mot de passe (au moins 6 caractères) :'
        );

        if (pw) {
          const { error } = await db.auth.updateUser({
            password: pw
          });

          notice(
            error ? error.message : 'Mot de passe mis à jour.',
            !!error
          );
        }
      }, 0);
    }

    if (
      event === 'SIGNED_IN' ||
      event === 'SIGNED_OUT' ||
      event === 'USER_UPDATED'
    ) {
      setTimeout(boot, 0);
    }
  });

  $('refresh').onclick = boot;
  $('reload').onclick = load;

  async function load() {
    notice('');

    let all = [];
    let offset = 0;

    while (true) {
      const { data, error } = await db
        .from('articles')
        .select(
          'id,title,url,source,published_at,found_at,orchestra,category,summary,review_status'
        )
        .order('published_at', {
          ascending: false,
          nullsFirst: false
        })
        .range(offset, offset + 499);

      if (error) {
        notice('Erreur de lecture : ' + error.message, true);
        return;
      }

      all.push(...(data || []));

      if (!data || data.length < 500) break;

      offset += 500;

      if (offset >= 5000) {
        notice(
          'Affichage limité aux 5 000 articles les plus récents.'
        );
        break;
      }
    }

    records = all;
    populate();
    shown = pageSize;
    render();
  }

  function populate() {
    const fields = [
      [
        'orchestra',
        [...new Set(
          records.map(x => x.orchestra).filter(Boolean)
        )]
      ],
      [
        'category',
        [...new Set(
          records.map(x => x.category).filter(Boolean)
        )]
      ]
    ];

    for (const [id, values] of fields) {
      const sel = $(id);
      const old = sel.value;

      sel.replaceChildren(new Option('Tous', ''));

      values
        .sort((a, b) => a.localeCompare(b, 'fr'))
        .forEach(x => sel.add(new Option(x, x)));

      sel.value = old;
    }
  }

  function filtered() {
    const q = $('search').value
      .trim()
      .toLocaleLowerCase('fr');

    return records.filter(a =>
      (
        !q ||
        [a.title, a.summary, a.source, a.orchestra]
          .some(x =>
            String(x || '')
              .toLocaleLowerCase('fr')
              .includes(q)
          )
      ) &&
      (
        !$('orchestra').value ||
        a.orchestra === $('orchestra').value
      ) &&
      (
        !$('category').value ||
        a.category === $('category').value
      ) &&
      (
        !$('status').value ||
        a.review_status === $('status').value
      )
    );
  }

  function render() {
    const items = filtered();

    $('total').textContent = records.length;

    $('unreviewed').textContent = records.filter(
      x => x.review_status === 'unreviewed'
    ).length;

    $('orchCount').textContent = new Set(
      records
        .map(x => x.orchestra)
        .filter(x => x && x !== 'Autres orchestres')
    ).size;

    $('count').textContent =
      `${items.length} résultat(s)`;

    const root = $('articles');
    root.replaceChildren();

    for (const a of items.slice(0, shown)) {
      const el = document.createElement('article');
      el.className = 'card';

      const date = a.published_at
        ? new Date(a.published_at).toLocaleDateString('fr-FR')
        : 'Date inconnue';

      el.innerHTML = `
        <div class="meta">
          ${esc(date)} · ${esc(a.source || 'Source non renseignée')}
        </div>
        <h2>
          <a href="${esc(validUrl(a.url))}"
             target="_blank"
             rel="noopener noreferrer">
            ${esc(a.title)}
          </a>
        </h2>
        <span class="pill">
          ${esc(a.orchestra || 'Autres orchestres')}
        </span>
        <span class="pill">
          ${esc(a.category || 'Général')}
        </span>
        <p>${esc(a.summary || '')}</p>
        <div class="review">
          <span class="status">
            Statut : ${esc(
              statusText[a.review_status] || a.review_status
            )}
          </span>
        </div>
      `;

      if (isAdmin) {
        const row = el.querySelector('.review');

        for (const [st, label] of [
          ['validated', 'Valider'],
          ['rejected', 'Rejeter'],
          ['unreviewed', 'Réinitialiser']
        ]) {
          const b = document.createElement('button');
          b.className = 'secondary';
          b.textContent = label;
          b.disabled = a.review_status === st;
          b.onclick = () => review(a, st);
          row.append(b);
        }
      }

      root.append(el);
    }

    show('more', items.length > shown);
  }

  async function review(a, status) {
    const { error } = await db
      .from('articles')
      .update({
        review_status: status,
        reviewed_at: status === 'unreviewed'
          ? null
          : new Date().toISOString(),
        reviewed_by: status === 'unreviewed'
          ? null
          : currentUser.id
      })
      .eq('id', a.id);

    if (error) {
      notice(
        'Validation impossible : ' + error.message,
        true
      );
      return;
    }

    a.review_status = status;
    render();
  }

  for (const id of [
    'search',
    'orchestra',
    'category',
    'status'
  ]) {
    $(id).addEventListener(
      id === 'search' ? 'input' : 'change',
      () => {
        shown = pageSize;
        render();
      }
    );
  }

  $('more').onclick = () => {
    shown += pageSize;
    render();
  };

  $('export').onclick = () => {
    const cols = [
      'published_at',
      'orchestra',
      'category',
      'title',
      'source',
      'url',
      'review_status'
    ];

    const csv = [
      cols.join(','),
      ...filtered().map(a =>
        cols.map(k =>
          '"' +
          String(a[k] ?? '').replaceAll('"', '""') +
          '"'
        ).join(',')
      )
    ].join('\r\n');

    const blob = new Blob(
      ['\uFEFF' + csv],
      { type: 'text/csv;charset=utf-8' }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = 'observatoire-sudonpl.csv';
    link.click();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  // Service worker temporarily disabled during debugging.
  boot();
})();
