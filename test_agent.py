from src.agent.graph import build_graph


# ============================================================
# INITIAL STATE
# ============================================================

def create_initial_state():
    """
    Create a clean state for a new conversation.
    """

    return {
        "user_message": "",
        "messages": [],

        "intent": "",
        "entities": {},

        "tool_name": "",
        "tool_input": {},
        "tool_result": None,

        "last_tool_name": "",
        "last_tool_call_id": "",

        "retrieved_context": [],

        "confirmation_required": False,
        "confirmation_pending": False,
        "confirmed": False,

        # Booking workflow
        "pending_booking": None,
        "pending_booking_price": None,

        # Cancellation workflow
        "pending_cancellation": None,

        # Rescheduling workflow
        "pending_rescheduling": None,

        # Membership workflow
        "awaiting_membership": False,
        "pending_is_member": None,

        "final_answer": "",
        "error": None,
    }


# ============================================================
# PREPARE NEW TURN
# ============================================================

def prepare_new_turn(previous_state, user_message):
    """
    Prepare the state for a new user turn.

    Persistent workflow data:
        - conversation history
        - pending booking
        - pending booking price
        - pending cancellation
        - pending rescheduling
        - confirmation state
        - membership state

    Transient data:
        - current user message
        - current tool
        - current tool input/result
        - current final answer
        - previous error
    """

    new_state = create_initial_state()

    # ========================================================
    # CURRENT USER MESSAGE
    # ========================================================

    new_state["user_message"] = user_message

    # ========================================================
    # PRESERVE CONVERSATION HISTORY
    # ========================================================

    new_state["messages"] = list(
        previous_state.get("messages", [])
    )

    # ========================================================
    # PRESERVE PENDING BOOKING
    # ========================================================

    previous_booking = previous_state.get(
        "pending_booking"
    )

    if previous_booking:
        new_state["pending_booking"] = dict(
            previous_booking
        )

    # ========================================================
    # PRESERVE PENDING BOOKING PRICE
    # ========================================================

    previous_price = previous_state.get(
        "pending_booking_price"
    )

    if previous_price:
        if isinstance(previous_price, dict):
            new_state["pending_booking_price"] = dict(
                previous_price
            )
        else:
            new_state["pending_booking_price"] = (
                previous_price
            )

    # ========================================================
    # PRESERVE PENDING CANCELLATION
    #
    # Required for:
    #
    # User: Cancel booking BKG1007
    #
    # Then:
    #
    # User: yes
    #
    # The second turn must still know:
    #
    # pending_cancellation = {
    #     "booking_id": "BKG1007"
    # }
    # ========================================================

    previous_cancellation = previous_state.get(
        "pending_cancellation"
    )

    if previous_cancellation:
        if isinstance(previous_cancellation, dict):
            new_state["pending_cancellation"] = dict(
                previous_cancellation
            )
        else:
            new_state["pending_cancellation"] = (
                previous_cancellation
            )

    # ========================================================
    # PRESERVE PENDING RESCHEDULING
    # ========================================================

    previous_rescheduling = previous_state.get(
        "pending_rescheduling"
    )

    if previous_rescheduling:
        if isinstance(previous_rescheduling, dict):
            new_state["pending_rescheduling"] = dict(
                previous_rescheduling
            )
        else:
            new_state["pending_rescheduling"] = (
                previous_rescheduling
            )

    # ========================================================
    # PRESERVE CONFIRMATION STATE
    # ========================================================

    if previous_state.get("confirmation_pending"):
        new_state["confirmation_pending"] = True
        new_state["confirmation_required"] = True

    # ========================================================
    # PRESERVE CONFIRMED STATE
    # ========================================================

    new_state["confirmed"] = previous_state.get(
        "confirmed",
        False,
    )

    # ========================================================
    # PRESERVE MEMBERSHIP STATE
    # ========================================================

    new_state["awaiting_membership"] = previous_state.get(
        "awaiting_membership",
        False,
    )

    new_state["pending_is_member"] = previous_state.get(
        "pending_is_member"
    )

    # ========================================================
    # PRESERVE INTENT
    #
    # Important for multi-turn workflows.
    # ========================================================

    if previous_state.get("pending_cancellation"):
        new_state["intent"] = "cancellation"

    elif previous_state.get("pending_rescheduling"):
        new_state["intent"] = "rescheduling"

    elif previous_state.get("pending_booking"):
        new_state["intent"] = "booking"

    else:
        new_state["intent"] = previous_state.get(
            "intent",
            "",
        )

    return new_state


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # BUILD GRAPH
    # ========================================================

    graph = build_graph()

    # ========================================================
    # INITIAL STATE
    # ========================================================

    state = create_initial_state()

    # ========================================================
    # CHATBOT HEADER
    # ========================================================

    print("=" * 60)
    print("SPORTMATE AI")
    print("=" * 60)
    print("Sports Facility Booking Assistant")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 60)

    # ========================================================
    # CHAT LOOP
    # ========================================================

    while True:

        try:
            user_message = input("\nYou: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nSportMate: Goodbye!")
            break

        # ----------------------------------------------------
        # EMPTY INPUT
        # ----------------------------------------------------

        if not user_message:
            continue

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if user_message.lower() in {
            "exit",
            "quit",
        }:
            print("\nSportMate: Goodbye!")
            break

        # ====================================================
        # PREPARE CURRENT TURN
        # ====================================================

        state = prepare_new_turn(
            state,
            user_message,
        )

        # ====================================================
        # ADD USER MESSAGE TO HISTORY
        # ====================================================

        state["messages"].append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        # ====================================================
        # RUN GRAPH
        # ====================================================

        try:

            result = graph.invoke(state)

            # -----------------------------------------------
            # IMPORTANT:
            # Save the complete returned state.
            # -----------------------------------------------

            state = result

        except Exception as e:

            print(
                "\nSportMate: Sorry, something went wrong."
            )

            print(f"Error: {e}")

            # -----------------------------------------------
            # Preserve workflow state after an error.
            # -----------------------------------------------

            state = prepare_new_turn(
                state,
                "",
            )

            continue

        # ====================================================
        # FINAL ANSWER
        # ====================================================

        final_answer = result.get(
            "final_answer",
            "",
        )

        if final_answer:

            print("\nSportMate:")
            print(final_answer)

            # -----------------------------------------------
            # Store assistant response
            # -----------------------------------------------

            state.setdefault(
                "messages",
                [],
            )

            state["messages"].append(
                {
                    "role": "assistant",
                    "content": final_answer,
                }
            )

        else:

            print(
                "\nSportMate: "
                "I could not generate a response."
            )

        # ====================================================
        # ERROR
        # ====================================================

        if result.get("error"):

            print("\nError:")
            print(result["error"])


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
