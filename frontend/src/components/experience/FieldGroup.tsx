import { Children, cloneElement, isValidElement, type ReactNode, type ReactElement } from "react";

export default function FieldGroup({ label, children }: { label: string; children: ReactNode }) {
  return <fieldset className="input-field-group"><legend>{label}</legend>{Children.map(children, child => {
    if (isValidElement(child) && typeof child.type === "string" && ["input", "select", "textarea"].includes(child.type)) {
      const field = child as ReactElement<{ "aria-label"?: string }>;
      return cloneElement(field, { "aria-label": field.props["aria-label"] || label });
    }
    return child;
  })}</fieldset>;
}
