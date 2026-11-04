<template>
  <!-- The key recreates the path when the selection changes: WebKit does not repaint the
       markers when only marker-start/marker-end are switched on an existing path. -->
  <BaseEdge
    :key="selected ? 'selected' : 'default'"
    :id="id"
    :path="edgePath"
    :marker-start="scopedMarkerStart"
    :marker-end="scopedMarkerEnd"
  />
</template>

<script>
import {
  BaseEdge,
  getBezierPath,
  getSmoothStepPath,
  Position,
} from "@vue-flow/core";

export default {
  name: "ErdRelationEdge",
  components: {
    BaseEdge,
  },
  props: {
    id: { type: String, required: true },
    sourceX: { type: Number, required: true },
    sourceY: { type: Number, required: true },
    targetX: { type: Number, required: true },
    targetY: { type: Number, required: true },
    sourcePosition: { type: String, required: true },
    targetPosition: { type: String, required: true },
    source: { type: String, required: true },
    target: { type: String, required: true },
    data: { type: Object, required: false },
    markerEnd: { type: [String, Object], required: false },
    markerStart: { type: [String, Object], required: false },
    tabId: { type: String, required: false },
    selected: { type: Boolean, default: false },
    sourceHandleId: {
      type: String,
      default: "",
    },
    targetHandleId: {
      type: String,
      default: "",
    },
  },
  computed: {
    scopedMarkerStart() {
      return this.scopeMarker(this.markerStart);
    },
    scopedMarkerEnd() {
      return this.scopeMarker(this.markerEnd);
    },
    shouldUseSmoothStep() {
      const sourceSide = this.getHandleSide(this.sourceHandleId);
      const targetSide = this.getHandleSide(this.targetHandleId);

      if (!sourceSide || !targetSide) {
        return false;
      }

      if (sourceSide === targetSide) {
        return true;
      }

      // Opposite-side routes: right-left or left-right.
      // If the handles are too close horizontally, Bezier can look almost straight
      // or visually awkward, so use smoothstep earlier.
      return this.isOppositeSideRouteTooClose(sourceSide, targetSide);
    },
    pathData() {
      if (this.shouldUseSmoothStep) {
        return getSmoothStepPath({
          sourceX: this.sourceX,
          sourceY: this.sourceY,
          sourcePosition: this.sourcePosition,

          targetX: this.targetX,
          targetY: this.targetY,
          targetPosition: this.targetPosition,

          offset: 25,
        });
      }
      return this.getBezierPathWithOffset({
        sourceX: this.sourceX,
        sourceY: this.sourceY,
        sourcePosition: this.sourcePosition,

        targetX: this.targetX,
        targetY: this.targetY,
        targetPosition: this.targetPosition,

        offset: 25,
        curvature: 0.3,
      });
    },

    edgePath() {
      return this.pathData[0];
    },
  },
  methods: {
    scopeMarker(marker) {
      if (typeof marker !== "string" || !this.tabId) {
        return marker;
      }

      const variant = this.selected ? "-selected" : "";
      return marker.replace(/#([^')]+)/, `#$1${variant}-${this.tabId}`);
    },
    getHandleSide(handleId) {
      if (handleId?.endsWith("left")) {
        return "left";
      }

      if (handleId?.endsWith("right")) {
        return "right";
      }

      return null;
    },
    getPositionVector(position) {
      if (position === Position.Left) {
        return { x: -1, y: 0 };
      }

      if (position === Position.Right) {
        return { x: 1, y: 0 };
      }

      if (position === Position.Top) {
        return { x: 0, y: -1 };
      }

      if (position === Position.Bottom) {
        return { x: 0, y: 1 };
      }

      return { x: 0, y: 0 };
    },

    getOffsetPoint(x, y, position, offset) {
      const vector = this.getPositionVector(position);

      return {
        x: x + vector.x * offset,
        y: y + vector.y * offset,
      };
    },

    getBezierPathWithOffset({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
      offset = 30,
      curvature = 0.5,
    }) {
      const sourceOffset = this.getOffsetPoint(
        sourceX,
        sourceY,
        sourcePosition,
        offset,
      );

      const targetOffset = this.getOffsetPoint(
        targetX,
        targetY,
        targetPosition,
        offset,
      );

      const [middleBezierPath, labelX, labelY] = getBezierPath({
        sourceX: sourceOffset.x,
        sourceY: sourceOffset.y,
        sourcePosition,
        targetX: targetOffset.x,
        targetY: targetOffset.y,
        targetPosition,
        curvature,
      });

      const bezierCommandIndex = middleBezierPath.indexOf("C");
      const bezierCommand =
        bezierCommandIndex >= 0
          ? middleBezierPath.slice(bezierCommandIndex)
          : "";

      return [
        [
          `M ${sourceX},${sourceY}`,
          `L ${sourceOffset.x},${sourceOffset.y}`,
          bezierCommand,
          `L ${targetX},${targetY}`,
        ].join(" "),
        labelX,
        labelY,
      ];
    },
    isOppositeSideRouteTooClose(sourceSide, targetSide) {
      const MIN_BEZIER_HORIZONTAL_DISTANCE = 70;

      if (sourceSide === "right" && targetSide === "left") {
        return this.targetX - this.sourceX < MIN_BEZIER_HORIZONTAL_DISTANCE;
      }

      if (sourceSide === "left" && targetSide === "right") {
        return this.sourceX - this.targetX < MIN_BEZIER_HORIZONTAL_DISTANCE;
      }

      return false;
    },
  },
};
</script>
