// Build a virtual fMP4 layout from sample tables. Media bytes stay in the source.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/Eyevinn/mp4ff/mp4"
	"os"
)

type segment struct {
	Duration float64
	Header   []byte
	Ranges   [][2]uint64
}
type layout struct {
	Init     []byte
	Segments []segment
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}

func layoutFor(path string) layout {
	file, err := os.Open(path)
	check(err)
	defer file.Close()
	parsed, err := mp4.DecodeFile(file, mp4.WithDecodeMode(mp4.DecModeLazyMdat))
	check(err)
	if parsed.Moov == nil || parsed.IsFragmented() {
		panic("需要普通 MP4 样本表")
	}
	var video, audio *mp4.TrakBox
	for _, t := range parsed.Moov.Traks {
		switch t.Mdia.Hdlr.HandlerType {
		case "vide":
			if video == nil {
				video = t
			}
		case "soun":
			if audio == nil {
				audio = t
			}
		}
	}
	if video == nil {
		panic("未找到视频轨")
	}
	tracks := []*mp4.TrakBox{video}
	if audio != nil {
		tracks = append(tracks, audio)
	}
	init := mp4.CreateEmptyInit()
	init.Moov.Mvhd.Timescale = parsed.Moov.Mvhd.Timescale
	var ids []uint32
	for _, t := range tracks {
		kind := "video"
		if t == audio {
			kind = "audio"
		}
		dest := init.AddEmptyTrack(t.Mdia.Mdhd.Timescale, kind, t.Mdia.Mdhd.GetLanguage())
		desc := t.Mdia.Minf.Stbl.Stsd.Children
		if len(desc) != 1 {
			panic("不支持变化的编码配置")
		}
		dest.Mdia.Minf.Stbl.Stsd.AddChild(desc[0])
		if t.Edts != nil {
			dest.AddChild(t.Edts)
		}
		dest.Tkhd.Width, dest.Tkhd.Height = t.Tkhd.Width, t.Tkhd.Height
		ids = append(ids, dest.Tkhd.TrackID)
	}
	var buf bytes.Buffer
	check(init.Encode(&buf))
	out := layout{Init: buf.Bytes()}
	table := video.Mdia.Minf.Stbl
	scale := uint64(video.Mdia.Mdhd.Timescale)
	starts := []uint32{1}
	times := []uint64{0}
	last, dur, e := table.Stts.GetDecodeTime(video.GetNrSamples())
	check(e)
	endTime := last + uint64(dur)
	stat, e := file.Stat()
	check(e)
	// Aim for about 20 MiB at the original bitrate, bounded by the source GOP.
	// Slower-bitrate files can continue using two-second pieces.
	step := uint64(float64(endTime) * (20 * 1024 * 1024) / float64(stat.Size()))
	if step > 2*scale {
		step = 2 * scale
	}
	if step < scale/3 {
		step = scale / 3
	}
	next := step
	add := func(n uint32) {
		d, _, e := table.Stts.GetDecodeTime(n)
		check(e)
		if d >= next && endTime-d > scale/4 {
			starts = append(starts, n)
			times = append(times, d)
			next = d + step
		}
	}
	if table.Stss != nil {
		for _, n := range table.Stss.SampleNumber {
			add(n)
		}
	} else {
		for n := uint32(2); n <= video.GetNrSamples(); n++ {
			add(n)
		}
	}
	starts = append(starts, video.GetNrSamples()+1)
	times = append(times, last+uint64(dur))
	cursors := make([]uint32, len(tracks))
	for i := range cursors {
		cursors[i] = 1
	}
	for i := 0; i < len(starts)-1; i++ {
		frag, err := mp4.CreateMultiTrackFragment(uint32(i+1), ids)
		check(err)
		seg := segment{Duration: float64(times[i+1]-times[i]) / float64(scale)}
		for k, t := range tracks {
			end := starts[i+1]
			if t != video {
				end = t.GetNrSamples() + 1
				if i < len(starts)-2 {
					n, e := t.Mdia.Minf.Stbl.Stts.GetSampleNrAtTime(times[i+1] * uint64(t.Mdia.Mdhd.Timescale) / scale)
					if e == nil {
						end = n
					}
				}
			}
			begin := cursors[k]
			cursors[k] = end
			if begin >= end {
				continue
			}
			samples, e := t.GetSampleData(begin, end-1)
			check(e)
			dts, _, e := t.Mdia.Minf.Stbl.Stts.GetDecodeTime(begin)
			check(e)
			for _, s := range samples {
				check(frag.AddSampleToTrack(s, ids[k], dts))
				dts += uint64(s.Dur)
			}
			ranges, e := t.GetRangesForSampleInterval(begin, end-1)
			check(e)
			for _, r := range ranges {
				seg.Ranges = append(seg.Ranges, [2]uint64{r.Offset, r.Size})
			}
		}
		var h bytes.Buffer
		check(frag.Encode(&h))
		seg.Header = h.Bytes()
		out.Segments = append(out.Segments, seg)
	}
	return out
}
func main() {
	defer func() {
		if e := recover(); e != nil {
			fmt.Fprintln(os.Stderr, e)
			os.Exit(1)
		}
	}()
	check(json.NewEncoder(os.Stdout).Encode(layoutFor(os.Args[1])))
}
