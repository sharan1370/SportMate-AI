# SportMate AI

SportMate AI is a sports facility booking assistant with a Streamlit chat interface. A LangGraph workflow routes requests to Python tools for availability, pricing, booking management, and policy retrieval.

## Features

- Check availability for courts and other facilities.
- Create bookings through a multi-step flow with availability, price display, and explicit user confirmation.
- Cancel or reschedule existing bookings after confirmation.
- Look up facility pricing, equipment rental rates, and customer records.
- Answer questions using the SportMate policy knowledge base.
- Store resources, customers, and bookings in SQLite; use Chroma for policy retrieval.

## Architecture

```mermaid
flowchart TB
	visitor([User]) --> ui[Streamlit chat interface]
	ui --> session[(Streamlit session state)]
	session --> invoke[run_agent invokes compiled graph]
	invoke --> agent[Agent node resumes pending work or detects intent]
	agent --> has_tool{Tool selected?}
	has_tool -->|No| response[Return question, confirmation, or answer]
	has_tool -->|Yes| router[LangGraph routes to tool node]
	router --> execute[Tool node invokes registered StructuredTool]
	execute --> kind{Tool category}

	kind -->|Bookings and facility operations| domain[Availability, booking, cancellation, rescheduling, pricing, customers, resources]
	domain --> sqlite[(SQLite database)]
	seed[Seed script reads sample CSV and JSON] --> sqlite

	kind -->|Policy question| retrieval[Policy retrieval tool]
	retrieval --> query_embed[SentenceTransformer embeds query]
	query_embed --> chroma[(Persistent Chroma collection)]
	docs[Knowledge-base text files] --> ingest[Load, split, embed, and ingest]
	ingest --> chroma

	sqlite --> result[Tool result updates agent state]
	chroma --> result
	result --> next{Another tool queued?}
	next -->|Yes| router
	next -->|No| response
	response --> ui

	classDef people fill:#FFF0B3,stroke:#B7791F,stroke-width:2px,color:#422006;
	classDef interface fill:#CFFAFE,stroke:#0891B2,stroke-width:2px,color:#164E63;
	classDef orchestration fill:#DBEAFE,stroke:#2563EB,stroke-width:2px,color:#172554;
	classDef action fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D;
	classDef storage fill:#FCE7F3,stroke:#DB2777,stroke-width:2px,color:#831843;
	classDef retrieval fill:#EDE9FE,stroke:#7C3AED,stroke-width:2px,color:#3B0764;
	classDef decision fill:#FFEDD5,stroke:#EA580C,stroke-width:2px,color:#7C2D12;

	class visitor people;
	class ui,session interface;
	class invoke,agent,router,execute,result,response orchestration;
	class domain,seed,ingest action;
	class sqlite,chroma storage;
	class retrieval,query_embed,docs retrieval;
	class has_tool,kind,next decision;
```

### Request Lifecycle

```mermaid
flowchart TD
	message([User message]) --> check_state{Pending workflow in session?}
	check_state -->|Yes| resume[Continue pending workflow]
	check_state -->|No| classify[Detect intent and parse request]
	resume --> awaiting{Waiting for yes or no?}
	awaiting -->|Yes| pending_decision{User confirms?}
	pending_decision -->|Yes| run_pending[Run confirmed booking, cancellation, or rescheduling tool]
	run_pending --> answer
	pending_decision -->|No| reject_pending[Keep or clear pending request]
	reject_pending --> answer
	awaiting -->|No| merge_details[Merge newly provided details]
	merge_details --> required{Required details present?}
	classify --> branch{Request type}

	required -->|No| ask[Ask for missing details]
	required -->|Yes| branch

	branch -->|Book facility| booking_info[Collect facility, date, time, duration, name, phone]
	booking_info --> booking_ready{Details complete?}
	booking_ready -->|No| ask
	booking_ready -->|Yes| check_slot[Check availability]
	check_slot --> slot_free{Slot available?}
	slot_free -->|No| answer[Format result and reply]
	slot_free -->|Yes| quote[Calculate booking price]
	quote --> confirm_booking[Show quote and wait for explicit confirmation]
	confirm_booking --> approved{User confirms?}
	approved -->|Yes| validate[Validate customer and check availability again]
	validate --> save_booking[Create booking record in SQLite]
	save_booking --> answer
	approved -->|No| clear_booking[Clear pending booking]
	clear_booking --> answer

	branch -->|Cancel or reschedule| confirm_change[Collect booking details and request confirmation]
	confirm_change --> change_ok{User confirms?}
	change_ok -->|Yes| update_record[Run action tool and update SQLite]
	update_record --> answer
	change_ok -->|No| answer

	branch -->|Policy question| embed[Embed question and search Chroma]
	embed --> chunks[Return relevant knowledge-base passages]
	chunks --> answer
	branch -->|Availability, price, equipment, customer, resources| run_tool[Invoke matching registered tool]
	run_tool --> answer
	ask --> answer
	answer --> chat([Show response in Streamlit])

	classDef start fill:#FEF3C7,stroke:#D97706,stroke-width:2px,color:#78350F;
	classDef ui fill:#CFFAFE,stroke:#0891B2,stroke-width:2px,color:#164E63;
	classDef agent fill:#DBEAFE,stroke:#2563EB,stroke-width:2px,color:#172554;
	classDef booking fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D;
	classDef retrieval fill:#EDE9FE,stroke:#7C3AED,stroke-width:2px,color:#3B0764;
	classDef result fill:#FCE7F3,stroke:#DB2777,stroke-width:2px,color:#831843;
	classDef decision fill:#FFEDD5,stroke:#EA580C,stroke-width:2px,color:#7C2D12;

	class message,chat start;
	class answer,ask ui;
	class resume,classify,booking_info,check_slot,quote,confirm_booking,confirm_change,embed,chunks,run_tool,validate,save_booking,update_record,clear_booking agent;
	class booking_info,check_slot,quote,validate,save_booking,update_record booking;
	class embed,chunks retrieval;
	class answer result;
	class check_state,required,branch,booking_ready,slot_free,approved,change_ok decision;
```

### Components

- `app.py` renders the Streamlit chat, stores the transcript and pending conversation state, then invokes the graph once per user message.
- `src/agent/graph.py` compiles a LangGraph with an agent node and a tool execution node. Conditional routing runs tools when requested and ends the turn when the agent has a response or is waiting for confirmation.
- `src/agent/nodes.py` detects intents, extracts request details, preserves pending booking/cancellation/rescheduling/availability state, and formats tool results.
- `src/agent/tools.py` registers Python functions as LangChain `StructuredTool` instances. `src/tools/` contains the domain operations; `src/database/` provides SQLite access and seed loading.
- `src/rag/` loads policy documents, splits them into chunks, embeds them with `sentence-transformers/all-MiniLM-L6-v2`, and stores or retrieves vectors from Chroma.

Intent detection and detail extraction in the current request path are rule-based. A Groq client is initialized from configuration, and `GROQ_API_KEY` is currently required during startup; the graph does not make a chat-completion request for each message.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- A Groq API key

## Setup

1. Clone the repository and open its directory:

	```bash
	git clone https://github.com/sharan1370/SportMate-AI
	cd sportmate-ai
	```

2. Install the project dependencies:

	```bash
	uv sync
	```

3. Create a `.env` file in the project root and add your Groq API key. `GROQ_MODEL` defaults to `qwen/qwen3.6-27b`; current intent routing is rule-based, so changing this setting does not change the active request flow.

	```dotenv
	GROQ_API_KEY=your_groq_api_key
	# Optional
	GROQ_MODEL=qwen/qwen3.6-27b
	```

4. Create and seed the SQLite database with the sample resources, customers, and bookings:

	```bash
	uv run python -m src.database.seed
	```

5. Build the policy knowledge-base index in Chroma:

	```bash
	uv run python -m src.rag.ingest
	```

	The first ingestion downloads the `sentence-transformers/all-MiniLM-L6-v2` embedding model, so it can take a little longer and requires internet access.

## Run

Start the Streamlit app from the project root:

```bash
uv run streamlit run app.py
```

Streamlit prints a local URL in the terminal. Open it in a browser to use the assistant.

## Example Requests

- `Is BC1 available tomorrow at 7 PM for 1 hour?`
- `Book badminton court BC2 on 2026-09-20 at 7 PM for 1 hour`
- `How much is a badminton court for 1 hour?`
- `Cancel booking BKG1013`
- `Reschedule booking BKG1013`
- `How do cancellations and refunds work?`

Booking, cancellation, and rescheduling requests require confirmation before the corresponding change is made.

## Run Tests

Run the automated test suite with:

```bash
uv run pytest
```

## Project Structure

```text
app.py                 Streamlit user interface
src/agent/             LangGraph workflow, state, prompts, and tool registration
src/config/            Environment-based application settings
src/database/          SQLite connection, schema, repository, and seed data loader
src/rag/               Knowledge-base loading, embeddings, Chroma, and retrieval
src/tools/             Availability, booking, pricing, policy, and related tools
data/                  Sample resources, customers, and bookings
knowledge_base/        SportMate policy and facility information
tests/                 Automated tests
```

## Configuration and Data

`GROQ_API_KEY` is required to start the agent. Set `GROQ_MODEL` in `.env` to use a different Groq-supported model.

The seed command writes the local database to `db/booking.db`. The ingestion command writes the policy index to `vectorstore/chroma/`. Re-run these commands after changing the corresponding sample data or knowledge-base documents. Do not commit your `.env` file or expose API keys in source control.
