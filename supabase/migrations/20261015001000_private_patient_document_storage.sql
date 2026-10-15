-- Keep patient identity documents private; only the authenticated FastAPI server should access this bucket.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'nexuscare-patient-documents',
  'nexuscare-patient-documents',
  false,
  10485760,
  array['application/pdf', 'image/jpeg', 'image/png']
)
on conflict (id) do update
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['application/pdf', 'image/jpeg', 'image/png'];

-- Intentionally no anon/authenticated storage policies. The backend uses a server-only secret key.
