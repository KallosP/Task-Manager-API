create table
  public.tasks (
    id bigint generated by default as identity,
    name text null default ''::text,
    constraint tasks_pkey primary key (id)
  ) tablespace pg_default;