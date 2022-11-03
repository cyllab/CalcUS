var paraObject = JSON.parse("{{params_dict}}".replace(/&quot;/g, '"'));
for(var key in paraObject)
{
    if(Object.keys(paraObject[key]).length!=0)
    {
        const temp_para_map = new Map(Object.entries(paraObject[key]))
        para_map_map.set(parseInt(key), temp_para_map)
    }
}
for(i=0;i<db_id_array.length;i++)
{
    if(para_map_map.has(db_id_array[i]))
    {
        calc_para_map.set(db_id_map.get(db_id_array[i]), para_map_map.get(db_id_array[i]))
    }
}