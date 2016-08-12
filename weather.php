<?php

$hostname = 'localhost';
$username = 'weather_select';
$password = '##############';

try {
    $dbh = new PDO("mysql:host=$hostname;dbname=measurements",
                               $username, $password);

    /*** The SQL SELECT statement ***/
    $sth = $dbh->prepare("
    SELECT `dtg` AS date,
    `temperature` AS temperature,
    `humidity` AS humidity
    FROM `am2315`
    ORDER BY date DESC
    LIMIT 0,900
    ");
    $sth->execute();

    /* Fetch all of the remaining rows in the result set */
    $result = $sth->fetchAll(PDO::FETCH_ASSOC);

    /*** close the database connection ***/
    $dbh = null;
}
catch(PDOException $e)
    { echo $e->getMessage(); }

$json_data = json_encode($result);

?>
<!DOCTYPE html>
<meta charset="utf-8">
<style>

body { font: 12px Arial;}

path {
    stroke-width: 2;
    fill: none;
}

.axis path,
.axis line {
    fill: none;
    stroke: grey;
    stroke-width: 1;
    shape-rendering: crispEdges;
}

</style>
<body>
<script src="http://d3js.org/d3.v3.min.js"></script>

<script>

var margin = {top: 30, right: 55, bottom: 30, left: 60},
    width = 960 - margin.left - margin.right,
    height = 470 - margin.top - margin.bottom;

// Parse the date / time
var parseDate = d3.time.format("%Y-%m-%d %H:%M:%S").parse;

// specify the scales for each set of data
var x = d3.time.scale().range([0, width]);
var y0 = d3.scale.linear().range([height, 0]);
var y1 = d3.scale.linear().range([height, 0]);

// axis formatting
var xAxis = d3.svg.axis().scale(x)
    .orient("bottom");
var yAxisLeft = d3.svg.axis().scale(y0)
    .orient("left").ticks(5);
var yAxisRight = d3.svg.axis().scale(y1)
    .orient("right").ticks(5).tickFormat(d3.format(".0f"));

// line functions
var temperatureLine = d3.svg.line()
    .x(function(d) { return x(d.date); })
    .y(function(d) { return y0(d.temperature); });
var humidityLine = d3.svg.line()
    .x(function(d) { return x(d.date); })
    .y(function(d) { return y1(d.humidity); });

// seetup the svg area
var svg = d3.select("body")
    .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
    .append("g")
        .attr("transform",
              "translate(" + margin.left + "," + margin.top + ")");

// Get the data
<?php echo "data=".$json_data.";" ?>

// wrangle the data into the correct formats and units
data.forEach(function(d) {
	d.date = parseDate(d.date);
	d.temperature = +d.temperature;
	d.humidity = +d.humidity;
});

// Scale the range of the data
x.domain(d3.extent(data, function(d) { return d.date; }));
y0.domain([
    d3.min(data, function(d) {return Math.min(d.temperature); })-.25,
    d3.max(data, function(d) {return Math.max(d.temperature); })+.25]);
y1.domain([
    d3.min(data, function(d) {return Math.min(d.humidity); })-.25,
    d3.max(data, function(d) {return Math.max(d.humidity); })+.25]);

svg.append("path")      // Add the temperature line.
	.style("stroke", "steelblue")
	.attr("d", temperatureLine(data));

svg.append("path")      // Add the humidity line.
	.style("stroke", "red")
	.attr("d", humidityLine(data));

svg.append("g")         // Add the X Axis
	.attr("class", "x axis")
	.attr("transform", "translate(0," + height + ")")
	.call(xAxis);

svg.append("g")         // Add the temperature axis
	.attr("class", "y axis")
	.style("fill", "steelblue")
	.call(yAxisLeft);

svg.append("g")         // Add the humidity axis
	.attr("class", "y axis")
	.attr("transform", "translate(" + width + " ,0)")
	.style("fill", "red")
	.call(yAxisRight);

svg.append("text")      // Add the text label for the temperature axis
	.attr("transform", "rotate(-90)")
	.attr("x", 0)
	.attr("y", -30)
	.style("fill", "steelblue")
	.style("text-anchor", "end")
	.text("Temperature (Degrees Centigrade)");

svg.append("text")      // Add the text label for the humidity axis
	.attr("transform", "rotate(-90)")
	.attr("x", 0)
	.attr("y", width + 53)
	.style("fill", "red")
	.style("text-anchor", "end")
	.text("Humidity (% RH)");

</script>
</body>
