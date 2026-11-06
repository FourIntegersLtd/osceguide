# Console and circuit board match: named exceptions

- Spacing rhythm, 24px rows and 1px light selection borders (DESIGN.md "Spacing rhythm and quiet selection") stay; they drive most of tabs 1-3.
- Seed is 3 trainees x 3 stations; the boards draw 6 x 6. Reseeding to 6x6 made tab 2 worse (31.8% vs 15.3%), so it was reverted.
- Changed by hand (tab 8, 40%): the board is a card list in a fixed order with actor names; the api Intervention has actor_user_id only, and the app log is newest-first inside a fold.
- Add trainees dialog (17.6%): the board draws a disabled "not yet joined" row; the app keeps "Add them" disabled until someone is ticked.
- Circuit review (stations 19%, feedback 50%, record 39%): the app card lives in a narrower column with foundation paddings; not tuned further.
- Not scored: Console tabs 4, 5, 6, 9 (voice faults, a LiveKit room, a refused late arrival cannot be seeded locally); pause/extend/reset/resend/end/jump/redo dialogs (already PeopleDialog via OverrideDialog); EditCircuit, CircuitBuilder, NewCircuit boards.
