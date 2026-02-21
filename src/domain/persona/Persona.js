/**
 * Persona - entity representing an AI personality configuration.
 *
 * Encapsulates the persona type, system instruction, and voice settings
 * so the application layer doesn't need to know about prompt strings.
 */

import { fromString } from "./PersonaType.js";

export class Persona {
  /**
   * @param {{ type: string, systemInstruction: string, voiceName?: string }} params
   */
  constructor({ type, systemInstruction, voiceName = "Zephyr" }) {
    this.type = fromString(type);
    this.systemInstruction = systemInstruction;
    this.voiceName = voiceName;
  }

  /** Identifier string for the persona (matches PersonaType values). */
  get name() {
    return this.type;
  }
}
