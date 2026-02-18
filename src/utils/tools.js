import { FunctionCallDefinition } from "./gemini-api";

/**
 * Show Modal Dialog Tool
 * Displays a large modal dialog with a custom message
 */
export class ShowModalDialogTool extends FunctionCallDefinition {
  constructor(onShowModal) {
    super(
      "show_modal",
      "Displays a large modal dialog with a message to the user",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "The message to display in the modal",
          },
          title: {
            type: "string",
            description: "Optional title for the modal",
          },
        },
      },
      ["message"]
    );
    this.onShowModal = onShowModal;
  }

  functionToCall(parameters) {
    const message = parameters.message || "Alert!";
    const title = parameters.title;

    if (this.onShowModal) {
      this.onShowModal(message, title);
    }

    console.log(` Modal requested: ${title}: ${message}`);
  }
}

/**
 * Add CSS Style Tool
 * Injects CSS styles into the current page with !important flag
 */
export class AddCSSStyleTool extends FunctionCallDefinition {
  constructor() {
    super(
      "add_css_style",
      "Injects CSS styles into the current page with !important flag",
      {
        type: "object",
        properties: {
          selector: {
            type: "string",
            description:
              "CSS selector to target elements (e.g., 'body', '.class', '#id')",
          },
          property: {
            type: "string",
            description:
              "CSS property to set (e.g., 'background-color', 'font-size', 'display')",
          },
          value: {
            type: "string",
            description:
              "Value for the CSS property (e.g., 'red', '20px', 'none')",
          },
          styleId: {
            type: "string",
            description:
              "Optional ID for the style element (for updating existing styles)",
          },
        },
      },
      ["selector", "property", "value"]
    );
  }

  functionToCall(parameters) {
    const { selector, property, value, styleId } = parameters;

    // Create or find the style element
    let styleElement;
    if (styleId) {
      styleElement = document.getElementById(styleId);
      if (!styleElement) {
        styleElement = document.createElement("style");
        styleElement.id = styleId;
        document.head.appendChild(styleElement);
      }
    } else {
      styleElement = document.createElement("style");
      document.head.appendChild(styleElement);
    }

    // Create the CSS rule with !important
    const cssRule = `${selector} { ${property}: ${value} !important; }`;

    // Add the CSS rule to the style element
    if (styleId) {
      // If using an ID, replace the content
      styleElement.textContent = cssRule;
    } else {
      // Otherwise append to any existing content
      styleElement.textContent += cssRule;
    }

    console.log(`🎨 CSS style injected: ${cssRule}`);
    console.log(
      `   Applied to ${document.querySelectorAll(selector).length} element(s)`
    );
  }
}

/**
 * Report Visual State Tool
 * Reports what the AI observes from the camera feed
 */
export class ReportVisualStateTool extends FunctionCallDefinition {
  constructor(onReport) {
    super(
      "report_visual_state",
      "Reports the current visual observation from the camera feed. Call this when instructed by the system to check the camera. Describe what you see: the user's expression, posture, actions, and notable items.",
      {
        type: "object",
        properties: {
          description: {
            type: "string",
            description:
              "A concise description of what you currently see in the camera (in Japanese)",
          },
          user_emotion: {
            type: "string",
            description:
              "The detected emotion or state of the user (e.g., 笑顔, 困惑, 怒り, 普通, 不在)",
          },
          detected_items: {
            type: "string",
            description:
              "Comma-separated list of notable items or objects visible in the frame, in Japanese",
          },
        },
      },
      ["description"]
    );
    this.onReport = onReport;
  }

  functionToCall(parameters) {
    if (this.onReport) {
      this.onReport(parameters);
    }
    console.log(`👁️ Visual state: ${JSON.stringify(parameters)}`);
  }
}

/**
 * Celebrate Moment Tool
 * Triggered when the AI detects the user is happy or achieved something
 */
export class CelebrateMomentTool extends FunctionCallDefinition {
  constructor(onCelebrate) {
    super(
      "celebrate_moment",
      "Call this when the user seems happy, excited, or has achieved something. Shows a celebration card in the UI.",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "A celebratory message to display to the user, in Japanese",
          },
        },
      },
      ["message"]
    );
    this.onCelebrate = onCelebrate;
  }

  functionToCall(parameters) {
    if (this.onCelebrate) {
      this.onCelebrate(parameters.message);
    }
    console.log(`🎉 Celebrate: ${parameters.message}`);
  }
}

/**
 * Offer Support Tool
 * Triggered when the AI detects the user is sad, tired, or stressed
 */
export class OfferSupportTool extends FunctionCallDefinition {
  constructor(onSupport) {
    super(
      "offer_support",
      "Call this when the user seems sad, tired, or stressed. Shows a support card in the UI.",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "A supportive message to display to the user, in Japanese",
          },
        },
      },
      ["message"]
    );
    this.onSupport = onSupport;
  }

  functionToCall(parameters) {
    if (this.onSupport) {
      this.onSupport(parameters.message);
    }
    console.log(`💙 Support: ${parameters.message}`);
  }
}
