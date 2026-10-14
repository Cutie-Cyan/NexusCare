-- NexusCare: patient document verification, discount workflow, benefit estimates, price history, export audit.
-- Sensitive tables deliberately have RLS enabled and no browser policies: access is through the authenticated FastAPI backend.
CREATE TABLE IF NOT EXISTS public.patient_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
  document_type varchar(40) NOT NULL CHECK (document_type IN ('senior_id','pwd_id','philhealth_id','insurance','other')),
  storage_path text NOT NULL UNIQUE,
  original_filename varchar(255) NOT NULL,
  content_type varchar(120) NOT NULL,
  file_size_bytes bigint NOT NULL CHECK (file_size_bytes > 0 AND file_size_bytes <= 10485760),
  verification_status varchar(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','approved','rejected')),
  reviewed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  reviewed_at timestamptz,
  review_notes text,
  uploaded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((verification_status = 'pending' AND reviewed_at IS NULL) OR (verification_status <> 'pending' AND reviewed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_patient_documents_patient_status ON public.patient_documents(patient_id, verification_status);

CREATE TABLE IF NOT EXISTS public.discount_applications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
  bill_id uuid REFERENCES public.bills(id) ON DELETE RESTRICT,
  document_id uuid REFERENCES public.patient_documents(id) ON DELETE RESTRICT,
  discount_type varchar(30) NOT NULL CHECK (discount_type IN ('senior_citizen','pwd','philhealth','insurance','other')),
  requested_amount numeric(12,2) NOT NULL DEFAULT 0 CHECK (requested_amount >= 0),
  approved_amount numeric(12,2) NOT NULL DEFAULT 0 CHECK (approved_amount >= 0),
  status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','cancelled')),
  requested_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  reviewed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  reviewed_at timestamptz,
  review_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (approved_amount <= requested_amount OR requested_amount = 0),
  CHECK ((status IN ('pending','cancelled') AND reviewed_at IS NULL) OR (status IN ('approved','rejected') AND reviewed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_discount_applications_bill_status ON public.discount_applications(bill_id, status);
CREATE INDEX IF NOT EXISTS idx_discount_applications_patient_created ON public.discount_applications(patient_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.benefit_estimates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
  bill_id uuid REFERENCES public.bills(id) ON DELETE RESTRICT,
  estimate_type varchar(30) NOT NULL CHECK (estimate_type IN ('philhealth','insurance','discount')),
  gross_amount numeric(12,2) NOT NULL CHECK (gross_amount >= 0),
  estimated_coverage numeric(12,2) NOT NULL DEFAULT 0 CHECK (estimated_coverage >= 0),
  estimated_discount numeric(12,2) NOT NULL DEFAULT 0 CHECK (estimated_discount >= 0),
  estimated_patient_balance numeric(12,2) NOT NULL CHECK (estimated_patient_balance >= 0),
  rules_version varchar(80) NOT NULL,
  disclaimer text NOT NULL DEFAULT 'Estimate only; subject to eligibility, documentation, provider rules, and official adjudication.',
  calculated_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (estimated_coverage + estimated_discount <= gross_amount)
);
CREATE INDEX IF NOT EXISTS idx_benefit_estimates_patient_created ON public.benefit_estimates(patient_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.service_price_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  service_id uuid NOT NULL REFERENCES public.service_catalog(id) ON DELETE RESTRICT,
  previous_price numeric(12,2) CHECK (previous_price >= 0),
  new_price numeric(12,2) NOT NULL CHECK (new_price >= 0),
  effective_from timestamptz NOT NULL DEFAULT now(),
  changed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_service_price_history_service_effective ON public.service_price_history(service_id, effective_from DESC);

CREATE TABLE IF NOT EXISTS public.export_audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_profile_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  export_type varchar(60) NOT NULL,
  format varchar(10) NOT NULL CHECK (format IN ('xlsx','csv')),
  filters jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_count integer NOT NULL DEFAULT 0 CHECK (row_count >= 0),
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.patient_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discount_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.benefit_estimates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.service_price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.export_audit_events ENABLE ROW LEVEL SECURITY;
