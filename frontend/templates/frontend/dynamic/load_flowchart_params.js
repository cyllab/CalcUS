{% for key, value in params_dict.items %}
    {% for keys, values in value.items%}
        para_map.set("{{keys}}", "{{values}}")
        para_map_map.set(parseInt("{{key}}"), para_map)
    {% endfor %}
{% endfor %}

for(i=0;i<db_id_array.length;i++)
{
    if(para_map_map.has(db_id_array[i]))
    {
        calc_para_map.set(db_id_map.get(db_id_array[i]), para_map_map.get(db_id_array[i]))
    }
}