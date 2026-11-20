-- Keep a short table with its heading and optional short introduction.
-- Large tables remain breakable; this does not replace visual page review.
function Pandoc(doc)
  if FORMAT ~= 'typst' then return nil end
  local output = pandoc.List()
  local i = 1
  while i <= #doc.blocks do
    local last = i
    if doc.blocks[i].tag == 'Header' then
      local candidate = i + 1
      if doc.blocks[candidate] and doc.blocks[candidate].tag == 'Para'
          and #pandoc.utils.stringify(doc.blocks[candidate]) < 400 then
        candidate = candidate + 1
      end
      local t = doc.blocks[candidate]
      if t and t.tag == 'Table' then
        local rows = #t.head.rows + #t.foot.rows
        for _, body in ipairs(t.bodies) do
          rows = rows + #body.head + #body.body
        end
        if rows <= 9 and #pandoc.utils.stringify(t) < 1600 then last = candidate end
      end
    end
    if last > i then output:insert(pandoc.RawBlock('typst', '#block(breakable: false)[')) end
    for j = i, last do output:insert(doc.blocks[j]) end
    if last > i then output:insert(pandoc.RawBlock('typst', ']')) end
    i = last + 1
  end
  doc.blocks = output
  return doc
end
