import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders the application shell", () => {
  const { container } = render(<App />);
  expect(container).not.toBeEmptyDOMElement();
});
