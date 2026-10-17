-- Read-only checks. Never changes any article or member.
SELECT category, COUNT(*) AS articles, COUNT(*) FILTER (WHERE found_at >= now() - interval '7 days') AS last_7_days FROM public.articles GROUP BY category ORDER BY articles DESC;
SELECT review_status, COUNT(*) FROM public.articles GROUP BY review_status ORDER BY 2 DESC;
SELECT orchestra, COUNT(*) FROM public.articles GROUP BY orchestra ORDER BY 2 DESC LIMIT 40;
