-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.uf (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  nome character varying NOT NULL UNIQUE,
  sigla character varying NOT NULL UNIQUE,
  dt_criado timestamp without time zone NOT NULL,
  status character varying NOT NULL DEFAULT 'A'::character varying,
  dt_atualizado timestamp with time zone,
  usuario text NOT NULL DEFAULT 'Sistema'::text,
  CONSTRAINT uf_pkey PRIMARY KEY (id)
);
CREATE TABLE public.funcoes (
  id integer NOT NULL DEFAULT nextval('funcoes_id_seq'::regclass),
  nome text NOT NULL UNIQUE,
  status character NOT NULL DEFAULT 'A'::bpchar,
  dt_criado timestamp without time zone NOT NULL DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text) AT TIME ZONE 'America/Sao_Paulo'::text),
  dt_atualizado timestamp without time zone,
  usuario text,
  CONSTRAINT funcoes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.municipios (
  id integer NOT NULL DEFAULT nextval('municipios_id_seq'::regclass),
  nome text NOT NULL,
  uf_id integer NOT NULL,
  status character NOT NULL DEFAULT 'A'::bpchar,
  dt_criado timestamp without time zone NOT NULL DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text) AT TIME ZONE 'America/Sao_Paulo'::text),
  dt_atualizado timestamp without time zone,
  usuario text,
  CONSTRAINT municipios_pkey PRIMARY KEY (id),
  CONSTRAINT fk_uf_municipio FOREIGN KEY (uf_id) REFERENCES public.uf(id)
);
CREATE TABLE public.usuarios (
  id integer NOT NULL DEFAULT nextval('usuarios_id_seq'::regclass),
  nome text NOT NULL,
  funcao_id integer NOT NULL,
  status character NOT NULL DEFAULT 'A'::bpchar,
  dt_criado timestamp without time zone NOT NULL DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text) AT TIME ZONE 'America/Sao_Paulo'::text),
  dt_atualizado text,
  usuario text NOT NULL DEFAULT '''''Sistema''''::text'::text,
  CONSTRAINT usuarios_pkey PRIMARY KEY (id),
  CONSTRAINT fk_funcao_usuario FOREIGN KEY (funcao_id) REFERENCES public.funcoes(id)
);
CREATE TABLE public.emails (
  id integer NOT NULL DEFAULT nextval('emails_id_seq'::regclass),
  endereco_email text NOT NULL,
  usuario_id integer NOT NULL,
  status character NOT NULL DEFAULT 'A'::bpchar,
  dt_criado timestamp without time zone NOT NULL DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text) AT TIME ZONE 'America/Sao_Paulo'::text),
  dt_atualizado timestamp without time zone,
  usuario text,
  CONSTRAINT emails_pkey PRIMARY KEY (id),
  CONSTRAINT fk_usuario_email FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id)
);
CREATE TABLE public.clientes (
  id integer NOT NULL DEFAULT nextval('clientes_id_seq'::regclass),
  nome text NOT NULL,
  municipio_id integer NOT NULL,
  status character NOT NULL DEFAULT 'A'::bpchar,
  dt_criado timestamp without time zone NOT NULL DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text) AT TIME ZONE 'America/Sao_Paulo'::text),
  dt_atualizado timestamp without time zone,
  usuario text,
  CONSTRAINT clientes_pkey PRIMARY KEY (id),
  CONSTRAINT fk_municipio_cliente FOREIGN KEY (municipio_id) REFERENCES public.municipios(id)
);
CREATE TABLE public.origens (
  id integer NOT NULL DEFAULT nextval('origens_id_seq'::regclass),
  nome text NOT NULL,
  status character NOT NULL DEFAULT 'A'::bpchar,
  dt_criado timestamp without time zone NOT NULL DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text) AT TIME ZONE 'America/Sao_Paulo'::text),
  dt_atualizado timestamp without time zone,
  usuario text,
  CONSTRAINT origens_pkey PRIMARY KEY (id)
);
CREATE TABLE public.prioridades (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  nome text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'A'::text,
  dt_criado timestamp with time zone NOT NULL DEFAULT now(),
  dt_atualizado timestamp with time zone,
  usuario text,
  CONSTRAINT prioridades_pkey PRIMARY KEY (id)
);
CREATE TABLE public.motivos (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  nome text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'A'::text,
  dt_criado timestamp with time zone NOT NULL DEFAULT now(),
  dt_atualizado timestamp with time zone NOT NULL DEFAULT now(),
  usuario text NOT NULL DEFAULT 'Sistema'::text,
  CONSTRAINT motivos_pkey PRIMARY KEY (id)
);
CREATE TABLE public.modulos (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  nome text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'A'::text,
  dt_criado timestamp with time zone NOT NULL DEFAULT now(),
  dt_atualizado timestamp with time zone NOT NULL DEFAULT now(),
  usuario text NOT NULL DEFAULT 'Sistema'::text,
  CONSTRAINT modulos_pkey PRIMARY KEY (id)
);
CREATE TABLE public.funcionalidades (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  modulo_id integer NOT NULL,
  nome text NOT NULL,
  status text NOT NULL DEFAULT 'A'::text,
  dt_criado timestamp with time zone NOT NULL DEFAULT now(),
  dt_atualizado timestamp with time zone NOT NULL DEFAULT now(),
  usuario text NOT NULL DEFAULT 'Sistema'::text,
  CONSTRAINT funcionalidades_pkey PRIMARY KEY (id),
  CONSTRAINT funcionalidades_modulo_id_fkey FOREIGN KEY (modulo_id) REFERENCES public.modulos(id)
);
CREATE TABLE public.status (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  nome text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'A'::text,
  dt_criado timestamp with time zone NOT NULL DEFAULT now(),
  dt_atualizado timestamp with time zone NOT NULL DEFAULT now(),
  usuario text NOT NULL DEFAULT 'Sistema'::text,
  CONSTRAINT status_pkey PRIMARY KEY (id)
);
CREATE TABLE public.acoes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  is_novo boolean NOT NULL DEFAULT true,
  reaberto boolean NOT NULL DEFAULT false,
  usuario_id integer,
  motivo_id integer,
  funcionalidade_id integer,
  origem_id integer,
  status_id integer DEFAULT 1,
  prioridade_id bigint,
  cliente_id integer,
  chamado text,
  descricao_inicial text NOT NULL,
  observacoes text,
  protocolo text,
  inicio timestamp with time zone NOT NULL DEFAULT now(),
  fim timestamp with time zone,
  prazo_de_entrega timestamp with time zone,
  timer_pause_start timestamp with time zone,
  duracao_acumulada_segundos integer NOT NULL DEFAULT 0,
  comentarios jsonb NOT NULL DEFAULT '[]'::jsonb,
  anexos jsonb NOT NULL DEFAULT '[]'::jsonb,
  dt_criado timestamp with time zone NOT NULL DEFAULT now(),
  dt_atualizado timestamp with time zone NOT NULL DEFAULT now(),
  usuario_atualizacao text NOT NULL DEFAULT 'Sistema'::text,
  sentimento_id integer,
  municipio_id integer,
  CONSTRAINT acoes_pkey PRIMARY KEY (id),
  CONSTRAINT acoes_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id),
  CONSTRAINT acoes_motivo_id_fkey FOREIGN KEY (motivo_id) REFERENCES public.motivos(id),
  CONSTRAINT acoes_funcionalidade_id_fkey FOREIGN KEY (funcionalidade_id) REFERENCES public.funcionalidades(id),
  CONSTRAINT acoes_origem_id_fkey FOREIGN KEY (origem_id) REFERENCES public.origens(id),
  CONSTRAINT acoes_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status(id),
  CONSTRAINT acoes_prioridade_id_fkey FOREIGN KEY (prioridade_id) REFERENCES public.prioridades(id),
  CONSTRAINT acoes_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id),
  CONSTRAINT acoes_sentimento_id_fkey FOREIGN KEY (sentimento_id) REFERENCES public.sentimentos(id),
  CONSTRAINT acoes_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.municipios(id)
);
CREATE TABLE public.sentimentos (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  nome text NOT NULL UNIQUE,
  emoji text,
  status text NOT NULL DEFAULT 'A'::text,
  CONSTRAINT sentimentos_pkey PRIMARY KEY (id)
);
CREATE TABLE public.tmp_import_acoes (
  id text,
  novo text,
  municipio text,
  prio text,
  csm text,
  inicio text,
  fim text,
  motivo text,
  modulo text,
  funcionalidade text,
  canal text,
  status text,
  duracao text,
  chamado text,
  observacoes text,
  prazo_de_entrega text,
  comentarios text,
  anexos text,
  timer text,
  nome_do_cliente text,
  sentimento text,
  protocolo text,
  alerta_sla text
);