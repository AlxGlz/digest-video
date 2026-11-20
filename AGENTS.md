# Developing digest-video

This repository contains the portable skill and its reusable helpers. Keep developer plans, research, and private test runs in the separate development workspace provided with the task. The installed skill must work without that workspace or the development conversation.

Write the skill, its description, shipped instructions, reference material, and command documentation in English. The user's conversation and generated PDF/Markdown use the user's requested language. Preserve original quotations, code identifiers, and multilingual test data when needed for fidelity.

Use relative skill/run paths and existing environment capabilities. One agent must be able to complete the workflow. Preserve raw evidence, source locators, and reusable authored content for both output formats.

If you ask the user a question, end the turn and wait for the answer before continuing any work, including reading files. Parallel work while waiting requires the user's explicit request.

Keep recordings, attachments, model weights, binaries, generated outputs, and credentials outside tracked repository files. Publish only distributable code, instructions, and synthetic fixtures. Test changed helpers through their observable behavior; a structural validator does not establish content accuracy or visual quality.
