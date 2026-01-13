create schema if not exists audit;

create table audit.conversations (
  id uuid primary key,
  profile text not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  metadata jsonb not null default '{}'
);

create table audit.messages (
  id uuid primary key,
  conversation_id uuid not null references audit.conversations(id),
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'
);

create table audit.summaries (
  id uuid primary key,
  conversation_id uuid not null references audit.conversations(id),
  content text not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'
);

create index audit_messages_conversation_created_at_idx
  on audit.messages (conversation_id, created_at);

create index audit_summaries_conversation_created_at_idx
  on audit.summaries (conversation_id, created_at);
