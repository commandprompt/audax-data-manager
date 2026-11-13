const COLUMN_PADDING = 5;
const TABLE_HEADER_HEIGHT = 40 + COLUMN_PADDING;
const COLUMN_HEIGHT = 24;

const DEFAULT_LAYOUT_OPTIONS = {
  padding: 50,
  spacingFactor: 0.85,
  columnsPerRow: 5,
  tableGapX: 80,
  tableGapY: 80,
  snapGrid: [10, 10],
  offsetY: 0,
};

function snapValue(value, gridSize) {
  if (!gridSize) {
    return value;
  }

  return Math.round(value / gridSize) * gridSize;
}

function getNodeSize(node) {
  return {
    width: node.dimensions?.width,
    height: node.dimensions?.height,
  };
}

function getLayoutedNodes(nodes, internalNodes, options = {}) {
  const layoutOptions = {
    ...DEFAULT_LAYOUT_OPTIONS,
    ...options,
  };

  const [gridX, gridY] = layoutOptions.snapGrid;

  const tableNodes = nodes.filter((node) => node.type === "table");
  const tableReadNodes = internalNodes.filter((node) => node.type === "table");
  const tablePositions = {};

  const gapX = snapValue(
    layoutOptions.tableGapX * layoutOptions.spacingFactor,
    gridX,
  );

  const gapY = snapValue(
    layoutOptions.tableGapY * layoutOptions.spacingFactor,
    gridY,
  );

  let currentY = snapValue(layoutOptions.padding + layoutOptions.offsetY, gridY);
  let index = 0;

  for (
    let rowStart = 0;
    rowStart < tableNodes.length;
    rowStart += layoutOptions.columnsPerRow
  ) {
    const rowNodes = tableNodes.slice(
      rowStart,
      rowStart + layoutOptions.columnsPerRow,
    );

    let currentX = snapValue(layoutOptions.padding, gridX);
    let rowHeight = 0;

    rowNodes.forEach((node) => {
      let internalNode = tableReadNodes[index];
      const { width, height } = getNodeSize(internalNode);

      tablePositions[node.id] = {
        x: snapValue(currentX, gridX),
        y: snapValue(currentY, gridY),
      };

      currentX = snapValue(currentX + width + gapX, gridX);
      rowHeight = Math.max(rowHeight, height);
      index++;
    });

    currentY = snapValue(currentY + rowHeight + gapY, gridY);
  }

  return nodes.map((node) => {
    if (node.type !== "table") {
      return node;
    }

    return {
      ...node,
      position: tablePositions[node.id],
    };
  });
}

export { TABLE_HEADER_HEIGHT, COLUMN_HEIGHT, getLayoutedNodes };
