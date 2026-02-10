create schema if not exists audit;

create table audit.conversations (
  id text primary key,
  profile text not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  metadata jsonb not null default '{}'
);

create table audit.messages (
  id uuid primary key,
  conversation_id text not null references audit.conversations(id),
  role text not null check (role in ('user','assistant','system','summary')),
  content text not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'
);

create index audit_messages_conversation_created_at_idx
  on audit.messages (conversation_id, created_at);

create index audit_conversations_location_norm_idx
  on audit.conversations ((lower(trim(metadata->>'location'))));
