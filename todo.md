
- want to add posthog to try it
- social app previews (can use deArrow)
- tasteful extra features (hidden behind tools button)
    - if at all possible: silence skipper
        - we can seek the video through the iframe!
        - and change the playback rate (only up to 2x)
        - to get silence level, can't go direct to youtube
            - can process video silence timestamps server side (could be a public good database even)
            - could determine it from transcripts
                - can only get timed transcripts from internal yt api / wrapper library of it
                - not as accurate as downloading it and skipping the silence
    - copy transcript (they can paste in an ai to chat if they want... not on me though for those who hate ai)
    
    More:
    - shazam tool (copyrighted/unlicensed songs already in original vid description)
        - aware of current timestamp
    - skip sponsnors (can use video seek api + sponsorblock data)
    
    - had some other ideas i forgot'
    - A/B history (if can find api) (or link out or not)
    - skip sponsnors ()
    - maybe
        link to other youtube frontends
        - maybe "open this video in"
            - yt
            - other yt frontends
                - is linking these will make google mad at me?
            - viewstats
        - download (too tos-y)
        - notes / personal annotation section (probably not)
            - communal comments section or something like that but different
    
- other features
    - maybe: support playlists or custom playlists? (can create playlist urls even dynamically)
    - create community collaborative feeds of channels 
        - inspired by pockettube or by lists features of other apps
    - sign in with google to make sure it tracks your watch history...
    - &list= in url 
    
guidelines:
- we want to make sure to keep everything minimal and following progressive disclosure, users who do not care about a feature should not have to think about feature
(we will put "show video tools" dropdown and allow tools to be toggled on, or something along those lines, active tools will be in queryParams as well)