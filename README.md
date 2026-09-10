# XLR8 Social Media Agent

A **Python AI agent that writes and posts fitness content on autopilot** — it generates on-brand posts, attaches imagery, and publishes to Threads, Instagram and Facebook on a schedule. Dockerised and deployed on Railway.

## How it works

An agent loop generates content with a local **Ollama** model (llama3), falling back to the **Groq** cloud API when Ollama is offline. It sources imagery from **Pexels**, then publishes via the **Threads** and **Meta Graph** APIs on a daily schedule.

## Highlights

| Area | Detail |
| --- | --- |
| AI | Ollama (llama3) locally, with a Groq API cloud fallback |
| Publishing | Threads API + Meta Graph API (Instagram / Facebook) |
| Media | Pexels API for stock imagery |
| Scheduling | Posts daily; generates content on an interval |
| Deploy | Dockerised, runs on Railway |
| Config | All keys read from environment variables (`config.py` + `.env`) — nothing hardcoded |

## Stack

`Python` · `Ollama` · `Groq` · `Threads API` · `Meta Graph API` · `Docker` · `Railway`

## Run it

Set the environment variables listed in `config.py` (Meta/Threads tokens, Groq and Pexels keys), then run with Docker or deploy via `railway.toml`.

---

*Built by [Omar Bedoh](https://github.com/OmarBedoh) — a salesperson who builds AI. Open to SDR/BDR roles at AI and cybersecurity companies.*
