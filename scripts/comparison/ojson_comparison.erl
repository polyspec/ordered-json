%% Adapter only. Inputs and expectations come from the shared verifier.
-module(ojson_comparison).
-export([main/0]).

main() ->
    case io:get_line("") of
        eof -> ok;
        Line ->
            Path = string:trim(Line, trailing, "\r\n"),
            {ok, Source} = file:read_file(Path),
            Result = observe(Source),
            io:put_chars([ojson:'encode!'(Result), $\n]),
            main()
    end.

observe(Source) ->
    Decoded = try ojson:decode(Source)
    catch Class:_ -> #{ok => false, decode_error => atom_to_binary(Class, utf8)} end,
    case Decoded of
        {ok, Value} ->
            Inspection = try #{ok => true, tree => tree(Value, 0)}
                catch _:Reason -> #{ok => true, tree_error => atom_to_binary(Reason, utf8)} end,
            try ojson:encode(Value) of
                {ok, Output} -> Inspection#{output => Output};
                {error, _} -> Inspection#{encode_error => <<"error">>}
            catch
                EncodeClass:_ -> Inspection#{encode_error => atom_to_binary(EncodeClass, utf8)}
            end;
        {error, _} -> #{ok => false, decode_error => <<"error">>};
        Failure -> Failure
    end.

tree(_, Depth) when Depth > 256 -> throw(inspection_depth_limit);
tree(Value, Depth) when is_map(Value) ->
    [<<"object">>, [[Key, tree(Child, Depth + 1)] || {Key, Child} <- maps:to_list(Value)]];
tree(Value, Depth) when is_list(Value) -> [<<"array">>, [tree(Child, Depth + 1) || Child <- Value]];
tree(Value, _) when is_binary(Value) -> [<<"string">>, Value];
tree(Value, _) when is_integer(Value) -> [<<"number">>, integer_to_binary(Value)];
tree(Value, _) when is_float(Value) -> [<<"number">>, float_to_binary(Value, [short])];
tree(true, _) -> [<<"boolean">>, true];
tree(false, _) -> [<<"boolean">>, false];
tree(nil, _) -> [<<"null">>].
