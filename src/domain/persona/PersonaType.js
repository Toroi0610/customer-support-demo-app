/**
 * PersonaType - value object enumerating supported AI personalities.
 */

export const PersonaType = Object.freeze({
  BRIGHT_FRIEND: "bright_friend",
  GENTLE_TEACHER: "gentle_teacher",
  MEAN_NEIGHBOR: "mean_neighbor",
  STUPID_DOG: "stupid_dog",
  LOVER_MALE: "lover_male",
  LOVER_FEMALE: "lover_female",
});

/**
 * Parse a persona string. Falls back to BRIGHT_FRIEND for unknown values.
 * @param {string} value
 * @returns {string} PersonaType constant
 */
export function fromString(value) {
  return Object.values(PersonaType).includes(value)
    ? value
    : PersonaType.BRIGHT_FRIEND;
}
