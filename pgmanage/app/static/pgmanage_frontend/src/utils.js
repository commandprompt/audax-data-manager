function truncateText(text, maxLength) {
  if (!text) return "";
  if (text.length <= maxLength) {
    return text;
  } else if (text.indexOf("/") !== -1) {
    const ellipsis = "...";
    const parts = text.split("/");
    const firstPart = parts[0];
    const lastPart = parts[parts.length - 1];
    const middleParts = parts.slice(1, parts.length - 1);
    let truncatedText = firstPart + "/";
    for (let i = 0; i < middleParts.length; i++) {
      if (
        truncatedText.length + middleParts[i].length + ellipsis.length >
        maxLength
      ) {
        truncatedText += ellipsis;
        break;
      }
      truncatedText += middleParts[i] + "/";
    }
    truncatedText += "/" + lastPart;
    return truncatedText;
  } else {
    const ellipsis = "...";
    const truncatedText = text.slice(0, maxLength - ellipsis.length) + ellipsis;
    return truncatedText;
  }
}

function extractOrderByClause(queryFilter) {
  const orderByRegex = /\bORDER\s+BY\s+([\w\s",.]+)$/i;
  const match = queryFilter.match(orderByRegex);

  if (!match) return { queryFilterCleaned: queryFilter, orderByClause: "" };

  const queryFilterCleaned = queryFilter.replace(orderByRegex, "").trim();
  return { queryFilterCleaned, orderByClause: `ORDER BY ${match[1]}` };
}

function findNode(node, predicate) {
  if (predicate(node)) return node;
  for (let child of node.children || []) {
    const found = findNode(child, predicate);
    if (found) return found;
  }
  return null;
}

function findChild(node, type) {
  return (node.children || []).find((child) => child.data?.type === type);
}

function splitStringInHalf(str) {
  const middleIndex = Math.ceil(str.length / 2);
  const firstHalf = str.slice(0, middleIndex);
  const secondHalf = str.slice(middleIndex);
  return [firstHalf, secondHalf];
}

function flashHighlight(el) {
  if (!el) return;
  const clearHighlight = () => el.classList.remove("focus-highlight");
  el.classList.remove("focus-highlight");
  void el.offsetWidth;
  el.classList.add("focus-highlight");
  el.addEventListener("animationend", clearHighlight, { once: true });
  el.addEventListener("animationcancel", clearHighlight, { once: true });
}

const ALLOWED_HTML_TAGS = [
  "B",
  "BR",
  "STRONG",
  "I",
  "EM",
  "MARK",
  "SMALL",
  "DEL",
  "INS",
  "SUB",
  "SUP",
];

// Check that the HTML has only allowed tags and no attributes.
function isSafeHtml(html) {
  const template = document.createElement("template");
  template.innerHTML = html;

  return [...template.content.querySelectorAll("*")].every(
    (node) =>
      ALLOWED_HTML_TAGS.includes(node.tagName) && node.attributes.length === 0
  );
}

export {
  truncateText,
  extractOrderByClause,
  findChild,
  findNode,
  splitStringInHalf,
  flashHighlight,
  isSafeHtml,
};
