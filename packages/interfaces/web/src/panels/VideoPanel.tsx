import { config } from "../state/store";

// Shows the live stream if INTERFACES_VIDEO_URL is set: <video> for file /
// HLS-style URLs, <img> for MJPEG streams.
export function VideoPanel() {
  const url = config.value?.video_url;
  const isVideo = url && /\.(mp4|webm|ogg|m3u8)(\?|$)/i.test(url);
  return (
    <section class="panel video">
      <h3>Live video</h3>
      {!url ? (
        <div class="video-placeholder">No video stream configured</div>
      ) : isVideo ? (
        <video src={url} autoPlay muted playsInline />
      ) : (
        <img src={url} alt="Live arena video" />
      )}
    </section>
  );
}
