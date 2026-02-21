/**
 * AudioStreamer - infrastructure component for microphone capture.
 *
 * Re-exports the existing AudioStreamer from media-utils.js so the
 * infrastructure layer has a canonical import path, keeping media
 * concerns separate from AI protocol concerns.
 */

export { AudioStreamer } from "../../utils/media-utils.js";
